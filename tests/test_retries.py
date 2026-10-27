import time

from helpers import entries, fast, pending, settle, wait_until
from rillkit import Broker, Message


def test_failing_handler_delivered_max_retries_plus_one_then_dead_lettered(broker: Broker, r, name):
    deliveries = []

    @broker.subscribe(name, group="g", max_retries=2, **fast())
    def handle(msg: Message):
        deliveries.append(msg.deliveries)
        raise ValueError("nope")

    broker.start()
    entry_id = broker.publish(name, {"a": 1})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    settle(0.5)  # a fourth delivery would show up here
    assert deliveries == [1, 2, 3]
    assert pending(r, name) == 0
    [(_, fields)] = entries(r, f"{name}-dlq")
    assert fields["x-original-id"] == entry_id
    assert fields["x-stream"] == name
    assert fields["x-group"] == "g"
    assert "nope" in fields["x-error"]
    assert fields["x-deliveries"] == "3"
    assert fields["data"] == '{"a": 1}'
    assert r.xlen(name) == 1  # the original stays in the stream, only the PEL entry is gone


def test_max_retries_zero_dead_letters_on_first_failure(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", max_retries=0, **fast())
    def handle(body):
        calls.append(1)
        raise ValueError("x")

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    settle(0.4)
    assert len(calls) == 1
    assert entries(r, f"{name}-dlq")[0][1]["x-deliveries"] == "1"


def test_max_retries_none_retries_beyond_default(broker: Broker, r, name):
    calls = []

    @broker.subscribe(name, group="g", max_retries=None, block_ms=50, claim_idle_ms=60)
    def handle(body):
        calls.append(1)
        raise ValueError("x")

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: len(calls) >= 6)
    assert r.xlen(f"{name}-dlq") == 0


def test_error_text_is_truncated_in_dlq(broker: Broker, r, name):
    @broker.subscribe(name, group="g", max_retries=0, **fast())
    def handle(body):
        raise ValueError("e" * 5000)

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    assert len(entries(r, f"{name}-dlq")[0][1]["x-error"]) <= 1000


def test_backoff_multiplier_spaces_out_retries(broker: Broker, r, name):
    times = []

    @broker.subscribe(name, group="g", max_retries=2, backoff=4.0, block_ms=50, claim_idle_ms=100)
    def handle(body):
        times.append(time.monotonic())
        raise ValueError("x")

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1, timeout=15)
    first_gap = times[1] - times[0]
    second_gap = times[2] - times[1]
    assert first_gap >= 0.09  # claim_idle_ms * 4 ** 0
    assert second_gap >= 0.38  # claim_idle_ms * 4 ** 1


def test_required_idle_is_capped_by_max_backoff(broker: Broker, name):
    @broker.subscribe(name, group="g", claim_idle_ms=100, backoff=10.0, max_backoff_ms=500)
    def handle(body): ...

    sub = broker.subscribers[0]
    assert sub._required_idle_ms(1) == 100
    assert sub._required_idle_ms(2) == 500
    assert sub._required_idle_ms(5) == 500


def test_crashed_consumer_message_is_claimed_after_idle_time(broker: Broker, r, name):
    r.xgroup_create(name, "g", id="0", mkstream=True)
    entry_id = broker.publish(name, {"lost": True})
    read = r.xreadgroup("g", "dead-consumer", {name: ">"}, count=1)
    assert len(read[0][1]) == 1  # delivered to a consumer that will never ack
    got = []

    @broker.subscribe(name, group="g", consumer="alive", **fast())
    def handle(msg: Message):
        got.append((msg.id, msg.deliveries, msg.consumer, msg.body))

    broker.start()
    assert wait_until(lambda: got and pending(r, name) == 0)
    assert got == [(entry_id, 2, "alive", {"lost": True})]


def test_crashed_message_not_claimed_before_idle_time(broker: Broker, r, name):
    r.xgroup_create(name, "g", id="0", mkstream=True)
    broker.publish(name, {})
    r.xreadgroup("g", "dead-consumer", {name: ">"}, count=1)
    got = []

    @broker.subscribe(name, group="g", claim_idle_ms=60_000, block_ms=50)
    def handle(body):
        got.append(body)

    broker.start()
    settle(0.4)
    assert got == []
    assert pending(r, name) == 1


def test_crashed_message_with_exhausted_retries_goes_to_dlq(broker: Broker, r, name):
    r.xgroup_create(name, "g", id="0", mkstream=True)
    entry_id = broker.publish(name, {})
    # simulate three earlier deliveries by claiming it repeatedly under other names
    r.xreadgroup("g", "c0", {name: ">"}, count=1)
    for i in range(1, 3):
        time.sleep(0.01)
        r.xclaim(name, "g", f"c{i}", 0, [entry_id])
    calls = []

    @broker.subscribe(name, group="g", max_retries=2, **fast())
    def handle(body):
        calls.append(body)

    broker.start()
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    assert calls == []
    assert pending(r, name) == 0
    assert entries(r, f"{name}-dlq")[0][1]["x-error"] == "retries exhausted"


def test_entry_trimmed_while_pending_is_dropped(broker: Broker, r, name):
    r.xgroup_create(name, "g", id="0", mkstream=True)
    entry_id = broker.publish(name, {"gone": True})
    r.xreadgroup("g", "dead-consumer", {name: ">"}, count=1)
    r.xdel(name, entry_id)
    got = []

    @broker.subscribe(name, group="g", **fast())
    def handle(body):
        got.append(body)

    broker.start()
    assert wait_until(lambda: pending(r, name) == 0)
    settle(0.3)
    assert got == []
    assert r.xlen(f"{name}-dlq") == 0


def test_replay_dlq_moves_entries_back_and_strips_context(broker: Broker, r, name):
    dlq = f"{name}-dlq"
    for i in range(3):
        r.xadd(dlq, {"data": f'{{"i": {i}}}', "x-original-id": "1-0", "x-error": "bad"})
    assert broker.replay_dlq(name, count=2) == 2
    assert r.xlen(dlq) == 1
    moved = entries(r, name)
    assert [f for _, f in moved] == [{"data": '{"i": 0}'}, {"data": '{"i": 1}'}]
    assert broker.replay_dlq(name) == 1
    assert broker.replay_dlq(name) == 0
    assert r.xlen(dlq) == 0


def test_replayed_message_is_consumed_again(broker: Broker, r, name):
    ok = []
    mode = {"fail": True}

    @broker.subscribe(name, group="g", max_retries=0, **fast())
    def handle(body):
        if mode["fail"]:
            raise ValueError("first time fails")
        ok.append(body)

    broker.start()
    broker.publish(name, {"x": 1})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    mode["fail"] = False
    assert broker.replay_dlq(name) == 1
    assert wait_until(lambda: ok == [{"x": 1}])
    assert wait_until(lambda: pending(r, name) == 0)


def test_replay_dlq_with_custom_dlq(broker: Broker, r, name):
    from rillkit import Stream

    s = Stream(name, group="g", dlq=f"{name}-dead")
    r.xadd(s.dlq_name, {"data": "{}", "x-error": "e"})
    assert broker.replay_dlq(s) == 1
    assert r.xlen(name) == 1


def test_nack_without_reason_still_records_an_error(make_broker, r, name):
    from helpers import fast, wait_until
    from rillkit import NackMessage, Stream

    broker = make_broker()
    stream = Stream(name, group="g")

    @broker.subscribe(stream, max_retries=0, **fast())
    def handle(body: dict):
        raise NackMessage()

    broker.start()
    broker.publish(stream, {"a": 1})
    assert wait_until(lambda: r.xlen(stream.dlq_name) == 1)
    fields = r.xrange(stream.dlq_name)[0][1]
    assert fields[b"x-error"] == b"NackMessage"
