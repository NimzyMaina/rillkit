import threading

import pytest
from pydantic import BaseModel

from helpers import entries, fast, pending, settle, wait_until
from rillkit import AckMessage, AckPolicy, Broker, Message, NackMessage, Stream


class Order(BaseModel):
    id: int
    sku: str


def test_subscribe_without_group_raises_value_error(broker: Broker, name):
    def handler(body): ...

    with pytest.raises(ValueError):
        broker.subscribe(name)(handler)
    with pytest.raises(ValueError):
        broker.subscribe(Stream(name))(handler)


def test_group_from_stream_object_or_argument(broker: Broker, name):
    @broker.subscribe(Stream(name, group="a"), **fast())
    def one(body): ...

    @broker.subscribe(name, group="b", **fast())
    def two(body): ...

    assert [s.stream.group for s in broker.subscribers] == ["a", "b"]


def test_subscribe_returns_handler_unchanged(broker: Broker, name):
    def handler(body): ...

    assert broker.subscribe(name, group="g")(handler) is handler


def test_dict_body_is_consumed_and_acked(broker: Broker, r, name):
    got = []

    @broker.subscribe(name, group="g", **fast())
    def handle(body):
        got.append(body)

    broker.start()
    broker.publish(name, {"a": 1, "b": [1, 2]})
    assert wait_until(lambda: got and pending(r, name) == 0)
    assert got == [{"a": 1, "b": [1, 2]}]


def test_existing_entries_are_consumed_with_default_group_start(broker: Broker, name):
    got = []
    broker.publish(name, {"n": 1})

    @broker.subscribe(name, group="g", **fast())
    def handle(body):
        got.append(body)

    broker.start()
    assert wait_until(lambda: got == [{"n": 1}])


def test_group_start_id_dollar_skips_old_entries(broker: Broker, name):
    got = []
    broker.publish(name, {"n": "old"})

    @broker.subscribe(name, group="g", group_start_id="$", **fast())
    def handle(body):
        got.append(body)

    broker.start()
    broker.publish(name, {"n": "new"})
    assert wait_until(lambda: got == [{"n": "new"}])


def test_start_twice_is_safe_for_existing_group(broker: Broker, r, name):
    @broker.subscribe(name, group="g", **fast())
    def handle(body): ...

    r.xgroup_create(name, "g", id="0", mkstream=True)
    broker.start()  # BUSYGROUP is swallowed
    assert wait_until(lambda: broker.subscribers[0]._thread.is_alive())


# pydantic

def test_model_handler_receives_validated_model(broker: Broker, r, name):
    got = []

    @broker.subscribe(name, group="g", **fast())
    def handle(order: Order):
        got.append(order)

    broker.start()
    broker.publish(name, Order(id=1, sku="x"))  # models are encoded too
    broker.publish(name, {"id": "2", "sku": "y"})  # coerced by pydantic
    assert wait_until(lambda: len(got) == 2 and pending(r, name) == 0)
    assert all(isinstance(o, Order) for o in got)
    assert [o.id for o in got] == [1, 2]


def test_invalid_model_goes_straight_to_dlq_without_retries(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", max_retries=5, **fast())
    def handle(order: Order):
        calls.append(order)

    broker.start()
    entry_id = broker.publish(name, {"id": "not-an-int"})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    [(_, fields)] = entries(r, f"{name}-dlq")
    assert fields["x-original-id"] == entry_id
    assert fields["x-deliveries"] == "1"
    assert "validation" in fields["x-error"]
    assert calls == []
    assert pending(r, name) == 0


def test_undecodable_json_goes_to_dlq(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", **fast())
    def handle(body):
        calls.append(body)

    broker.start()
    r.xadd(name, {"data": "{not json"})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    assert calls == []
    assert pending(r, name) == 0


def test_entry_without_data_field_goes_to_dlq(broker: Broker, r, name):
    @broker.subscribe(name, group="g", **fast())
    def handle(body): ...

    broker.start()
    r.xadd(name, {"other": "x"})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    assert "data" in entries(r, f"{name}-dlq")[0][1]["x-error"]


def test_custom_dlq_name(broker: Broker, r, name):
    @broker.subscribe(Stream(name, group="g", dlq=f"{name}-dead"), **fast())
    def handle(body): ...

    broker.start()
    r.xadd(name, {"data": "nope"})
    assert wait_until(lambda: r.xlen(f"{name}-dead") == 1)


# ack policies

def test_nack_on_error_success_acks(broker: Broker, r, name):
    done = threading.Event()

    @broker.subscribe(name, group="g", **fast())
    def handle(body):
        done.set()

    broker.start()
    broker.publish(name, {})
    assert done.wait(5)
    assert wait_until(lambda: pending(r, name) == 0)


def test_nack_on_error_failure_leaves_message_pending(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", max_retries=5, claim_idle_ms=60_000, block_ms=50)
    def handle(body):
        calls.append(1)
        raise RuntimeError("boom")

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: calls)
    assert wait_until(lambda: pending(r, name) == 1)
    assert r.xlen(f"{name}-dlq") == 0


def test_ack_always_acks_failures_without_retry_or_dlq(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", ack_policy=AckPolicy.ACK_ALWAYS, **fast())
    def handle(body):
        calls.append(1)
        raise RuntimeError("boom")

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: calls and pending(r, name) == 0)
    settle(0.5)
    assert len(calls) == 1
    assert r.xlen(f"{name}-dlq") == 0


def test_ack_always_acks_success(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", ack_policy="ack_always", **fast())
    def handle(body):
        calls.append(1)

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: calls and pending(r, name) == 0)


def test_ack_first_acks_before_handler_runs(broker: Broker, r, name):
    seen = []

    @broker.subscribe(name, group="g", ack_policy=AckPolicy.ACK_FIRST, **fast())
    def handle(body):
        seen.append(pending(r, name))
        raise RuntimeError("boom")

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: seen)
    assert seen == [0]
    settle(0.5)
    assert len(seen) == 1  # at most once, never retried
    assert r.xlen(f"{name}-dlq") == 0


def test_manual_without_ack_stays_pending(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", ack_policy=AckPolicy.MANUAL,
                      claim_idle_ms=60_000, block_ms=50)
    def handle(body):
        calls.append(1)

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: calls)
    settle(0.3)
    assert pending(r, name) == 1


def test_manual_msg_ack(broker: Broker, r, name):
    ids = []

    @broker.subscribe(name, group="g", ack_policy=AckPolicy.MANUAL,
                      claim_idle_ms=60_000, block_ms=50)
    def handle(msg: Message):
        assert pending(r, name) == 1
        msg.ack()
        assert msg.acked
        ids.append(msg.id)

    broker.start()
    mid = broker.publish(name, {})
    assert wait_until(lambda: ids == [mid] and pending(r, name) == 0)


def test_manual_msg_nack_is_retried_then_dead_lettered(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", ack_policy=AckPolicy.MANUAL, max_retries=1, **fast())
    def handle(msg: Message):
        calls.append(msg.deliveries)
        msg.nack()

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    assert calls == [1, 2]
    assert pending(r, name) == 0


def test_manual_exception_counts_as_nack(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", ack_policy=AckPolicy.MANUAL, max_retries=1, **fast())
    def handle(msg: Message):
        calls.append(1)
        raise RuntimeError("boom")

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    assert len(calls) == 2


def test_ack_after_nack_wins(broker: Broker, r, name):
    @broker.subscribe(name, group="g", ack_policy=AckPolicy.MANUAL, **fast())
    def handle(msg: Message):
        msg.nack()
        msg.ack()
        assert msg.acked and not msg.nacked

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: broker.subscribers[0]._thread.is_alive())
    assert wait_until(lambda: r.xlen(name) == 1 and pending(r, name) == 0)


def test_ack_message_exception_acks_even_with_nack_on_error(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", max_retries=5, **fast())
    def handle(body):
        calls.append(1)
        raise AckMessage()

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: calls and pending(r, name) == 0)
    settle(0.4)
    assert len(calls) == 1
    assert r.xlen(f"{name}-dlq") == 0


def test_nack_message_exception_retries_even_with_ack_always(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", ack_policy=AckPolicy.ACK_ALWAYS, max_retries=1, **fast())
    def handle(body):
        calls.append(1)
        raise NackMessage()

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    assert len(calls) == 2
    assert pending(r, name) == 0


# handler signatures

def _roundtrip(broker, name, handler, body=None):
    broker.subscribe(name, group="g", **fast())(handler)
    broker.start()
    broker.publish(name, {"k": "v"} if body is None else body)


def test_signature_message_annotated(broker: Broker, name):
    got = []

    def handle(m: Message):
        got.append(m)

    _roundtrip(broker, name, handle)
    assert wait_until(lambda: got)
    assert isinstance(got[0], Message)
    assert got[0].body == {"k": "v"}
    assert got[0].deliveries == 1
    assert got[0].stream.name == name
    assert got[0].consumer == broker.subscribers[0].consumer


@pytest.mark.parametrize("param", ["msg", "message"])
def test_signature_unannotated_msg_name_gets_message(broker: Broker, name, param):
    got = []
    ns = {"got": got}
    exec(f"def handle({param}):\n    got.append({param})\n", ns)
    _roundtrip(broker, name, ns["handle"])
    assert wait_until(lambda: got)
    assert isinstance(got[0], Message)


def test_signature_body_param_any_name(broker: Broker, name):
    got = []

    def handle(payload):
        got.append(payload)

    _roundtrip(broker, name, handle)
    assert wait_until(lambda: got == [{"k": "v"}])


def test_signature_body_and_message(broker: Broker, name):
    got = []

    def handle(payload: dict, msg: Message):
        got.append((payload, msg.id))

    _roundtrip(broker, name, handle)
    assert wait_until(lambda: got)
    assert got[0][0] == {"k": "v"}


def test_signature_model_and_message(broker: Broker, name):
    got = []

    def handle(order: Order, msg: Message):
        got.append((order, msg))

    _roundtrip(broker, name, handle, {"id": 3, "sku": "z"})
    assert wait_until(lambda: got)
    assert got[0][0] == Order(id=3, sku="z")


def test_signature_no_params(broker: Broker, name):
    got = []

    def handle():
        got.append(1)

    _roundtrip(broker, name, handle)
    assert wait_until(lambda: got)


def test_signature_two_body_params_raises_type_error(broker: Broker, name):
    def handle(a, b): ...

    with pytest.raises(TypeError):
        broker.subscribe(name, group="g")(handle)


def test_signature_model_and_body_raises_type_error(broker: Broker, name):
    def handle(order: Order, other): ...

    with pytest.raises(TypeError):
        broker.subscribe(name, group="g")(handle)


def test_signature_varargs_are_ignored(broker: Broker, name):
    got = []

    def handle(body, *args, **kwargs):
        got.append(body)

    _roundtrip(broker, name, handle)
    assert wait_until(lambda: got)
