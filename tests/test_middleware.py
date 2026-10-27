import json
from typing import Optional

from helpers import entries, fast, pending, read_count, settle, wait_until
from rillkit import AckMessage, BaseMiddleware, Idempotent, Message, PublishCommand, Stream


class Recorder(BaseMiddleware):
    def __init__(self, label: str, events: list[str]) -> None:
        self.label = label
        self.events = events

    def on_receive(self, msg: Message) -> None:
        self.events.append(f"{self.label}.on_receive")

    def consume_scope(self, call_next, msg):
        self.events.append(f"{self.label}.enter")
        try:
            return call_next(msg)
        finally:
            self.events.append(f"{self.label}.exit")

    def after_processed(self, msg: Message, exc: Optional[BaseException]) -> None:
        self.events.append(f"{self.label}.after:{type(exc).__name__ if exc else None}")


def test_hook_order_and_outermost_first(make_broker, r, name):
    events: list[str] = []
    broker = make_broker(middlewares=[Recorder("A", events), Recorder("B", events)])

    @broker.subscribe(name, group="g", **fast())
    def handle(body):
        events.append("handler")

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: "B.after:None" in events)
    assert events == [
        "A.on_receive", "B.on_receive",
        "A.enter", "B.enter", "handler", "B.exit", "A.exit",
        "A.after:None", "B.after:None",
    ]


def test_after_processed_receives_handler_exception(make_broker, r, name):
    seen = []

    class Spy(BaseMiddleware):
        def after_processed(self, msg, exc):
            seen.append(exc)

    broker = make_broker(middlewares=[Spy()])

    @broker.subscribe(name, group="g", max_retries=5, claim_idle_ms=60_000, block_ms=50)
    def handle(body):
        raise KeyError("bad")

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: seen)
    assert isinstance(seen[0], KeyError)


def test_after_processed_failure_does_not_break_consumer(make_broker, r, name):
    handled = []

    class Bad(BaseMiddleware):
        def after_processed(self, msg, exc):
            raise RuntimeError("middleware bug")

    broker = make_broker(middlewares=[Bad()])

    @broker.subscribe(name, group="g", **fast())
    def handle(body):
        handled.append(body)

    broker.start()
    broker.publish(name, {"n": 1})
    broker.publish(name, {"n": 2})
    assert wait_until(lambda: len(handled) == 2 and pending(r, name) == 0)


def test_after_processed_sees_message_acked_state(make_broker, r, name):
    states = []

    class Spy(BaseMiddleware):
        def after_processed(self, msg, exc):
            states.append((msg.acked, msg.nacked))

    broker = make_broker(middlewares=[Spy()])

    @broker.subscribe(name, group="g", **fast())
    def handle(body): ...

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: states)
    assert states == [(True, False)]


def test_consume_scope_can_short_circuit_with_ack_message(make_broker, r, name):
    handled = []

    class Skip(BaseMiddleware):
        def consume_scope(self, call_next, msg):
            raise AckMessage()

    broker = make_broker(middlewares=[Skip()])

    @broker.subscribe(name, group="g", **fast())
    def handle(body):
        handled.append(body)

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: pending(r, name) == 0 and r.xlen(name) == 1)
    settle(0.2)
    assert handled == []


def test_consume_scope_can_wrap_result_and_see_decoded_body(make_broker, r, name):
    seen = []

    class Spy(BaseMiddleware):
        def consume_scope(self, call_next, msg):
            seen.append(("before", msg.body))
            result = call_next(msg)
            seen.append(("after", result))
            return result

    broker = make_broker(middlewares=[Spy()])

    @broker.subscribe(name, group="g", **fast())
    def handle(body):
        return "r"

    broker.start()
    broker.publish(name, {"k": 1})
    assert wait_until(lambda: len(seen) == 2)
    assert seen == [("before", {"k": 1}), ("after", "r")]


def test_on_receive_runs_even_for_undecodable_messages(make_broker, r, name):
    received = []

    class Spy(BaseMiddleware):
        def on_receive(self, msg):
            received.append(msg.raw)

    broker = make_broker(middlewares=[Spy()])

    @broker.subscribe(name, group="g", **fast())
    def handle(body): ...

    broker.start()
    r.xadd(name, {"data": "garbage"})
    assert wait_until(lambda: received and r.xlen(f"{name}-dlq") == 1)
    assert received == [{"data": "garbage"}]


def test_publish_scope_can_mutate_command(make_broker, r, name):
    class Rewrite(BaseMiddleware):
        def publish_scope(self, call_next, cmd: PublishCommand):
            cmd.body = {**cmd.body, "stamped": True}
            cmd.stream = Stream(f"{name}-rewritten")
            return call_next(cmd)

    broker = make_broker(middlewares=[Rewrite()])
    entry_id = broker.publish(name, {"a": 1})
    assert r.xlen(name) == 0
    [(stored_id, fields)] = entries(r, f"{name}-rewritten")
    assert stored_id == entry_id
    assert json.loads(fields["data"]) == {"a": 1, "stamped": True}


def test_publish_scope_can_change_maxlen_and_sees_default(make_broker, r, name):
    seen = []

    class Spy(BaseMiddleware):
        def publish_scope(self, call_next, cmd):
            seen.append(cmd.maxlen)
            cmd.maxlen = 10
            return call_next(cmd)

    broker = make_broker(middlewares=[Spy()])
    for _ in range(500):
        broker.publish(Stream(name, maxlen=1000), {})
    assert set(seen) == {1000}
    assert r.xlen(name) < 500


def test_publish_scope_order_outermost_first(make_broker, name):
    events: list[str] = []

    class P(BaseMiddleware):
        def __init__(self, label):
            self.label = label

        def publish_scope(self, call_next, cmd):
            events.append(f"{self.label}>")
            result = call_next(cmd)
            events.append(f"<{self.label}")
            return result

    broker = make_broker(middlewares=[P("A"), P("B")])
    broker.publish(name, {})
    assert events == ["A>", "B>", "<B", "<A"]


def test_publish_scope_wraps_handler_return_value_publish(make_broker, r, name):
    published = []

    class Spy(BaseMiddleware):
        def publish_scope(self, call_next, cmd):
            published.append(cmd.stream.name)
            return call_next(cmd)

    broker = make_broker(middlewares=[Spy()])

    @broker.subscribe(name, group="g", **fast())
    @broker.publisher(f"{name}-out")
    def handle(body):
        return {"out": 1}

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: r.xlen(f"{name}-out") == 1)
    assert published == [name, f"{name}-out"]


def test_broker_level_runs_before_subscriber_level(make_broker, r, name):
    events: list[str] = []
    broker = make_broker(middlewares=[Recorder("broker", events)])

    @broker.subscribe(name, group="g", middlewares=[Recorder("sub", events)], **fast())
    def handle(body):
        events.append("handler")

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: "sub.after:None" in events)
    assert events[:2] == ["broker.on_receive", "sub.on_receive"]
    assert events[2:7] == ["broker.enter", "sub.enter", "handler", "sub.exit", "broker.exit"]


def test_subscriber_level_middleware_only_applies_to_that_subscriber(make_broker, r, name):
    events: list[str] = []
    broker = make_broker()
    other = f"{name}-other"

    @broker.subscribe(name, group="g", middlewares=[Recorder("sub", events)], **fast())
    def one(body): ...

    @broker.subscribe(other, group="g", **fast())
    def two(body): ...

    broker.start()
    broker.publish(other, {})
    assert wait_until(lambda: pending(r, other) == 0 and read_count(r, other) == 1)
    assert events == []
    broker.publish(name, {})
    assert wait_until(lambda: "sub.after:None" in events)


def test_middleware_added_after_subscribe_still_applies(make_broker, r, name):
    events: list[str] = []
    broker = make_broker()

    @broker.subscribe(name, group="g", **fast())
    def handle(body): ...

    mw = broker.use(Recorder("late", events))
    assert mw.broker is broker
    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: "late.after:None" in events)


def test_middleware_added_while_running_applies_to_next_messages(make_broker, r, name):
    events: list[str] = []
    broker = make_broker()

    @broker.subscribe(name, group="g", **fast())
    def handle(body): ...

    broker.start()
    broker.publish(name, {"n": 1})
    assert wait_until(lambda: pending(r, name) == 0 and read_count(r, name) == 1)
    broker.use(Recorder("live", events))
    broker.publish(name, {"n": 2})
    assert wait_until(lambda: "live.after:None" in events)
    assert events.count("live.on_receive") == 1


def test_middleware_gets_broker_reference_from_constructor_and_subscribe(make_broker, name):
    a, b = Recorder("a", []), Recorder("b", [])
    broker = make_broker(middlewares=[a])
    broker.subscribe(name, group="g", middlewares=[b])(lambda body: None)
    assert a.broker is broker and b.broker is broker


# Idempotent

def test_idempotent_skips_duplicates(make_broker, r, name):
    handled = []
    processed = []

    class Count(BaseMiddleware):
        def after_processed(self, msg, exc):
            processed.append(msg.id)

    broker = make_broker(middlewares=[Idempotent(key=lambda m: m.body["rid"]), Count()])

    @broker.subscribe(name, group="g", **fast())
    def handle(body):
        handled.append(body["rid"])

    broker.start()
    for rid in ("a", "a", "b", "a", "b"):
        broker.publish(name, {"rid": rid})
    assert wait_until(lambda: len(processed) == 5 and pending(r, name) == 0)
    assert handled == ["a", "b"]
    assert r.exists(f"rillkit:done:{name}:a")
    assert 0 < r.ttl(f"rillkit:done:{name}:a") <= 7 * 24 * 3600


def test_idempotent_does_not_record_failed_attempts(make_broker, r, name):
    attempts = []
    idem = Idempotent(key=lambda m: m.body["rid"], ttl=60, prefix="idem:")
    broker = make_broker(middlewares=[idem])

    @broker.subscribe(name, group="g", max_retries=3, **fast())
    def handle(body):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("first attempt fails")

    broker.start()
    broker.publish(name, {"rid": "x"})
    assert wait_until(lambda: len(attempts) == 2 and pending(r, name) == 0)
    assert r.exists(f"idem:{name}:x")
    assert r.ttl(f"idem:{name}:x") <= 60
