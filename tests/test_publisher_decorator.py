import json

from helpers import entries, fast, pending, read_count, settle, wait_until
from rillkit import Broker


def _out(r, stream):
    return [json.loads(f["data"]) for _, f in entries(r, stream)]


def test_subscribe_above_publisher_publishes_return_value(broker: Broker, r, name):
    out = f"{name}-out"

    @broker.subscribe(name, group="g", **fast())
    @broker.publisher(out)
    def handle(body):
        return {"doubled": body["n"] * 2}

    broker.start()
    broker.publish(name, {"n": 4})
    assert wait_until(lambda: _out(r, out) == [{"doubled": 8}])
    assert wait_until(lambda: pending(r, name) == 0)


def test_publisher_above_subscribe_publishes_return_value(broker: Broker, r, name):
    out = f"{name}-out"

    @broker.publisher(out)
    @broker.subscribe(name, group="g", **fast())
    def handle(body):
        return {"doubled": body["n"] * 2}

    broker.start()
    broker.publish(name, {"n": 5})
    assert wait_until(lambda: _out(r, out) == [{"doubled": 10}])


def test_none_return_does_not_publish(broker: Broker, r, name):
    out = f"{name}-out"
    calls = []

    @broker.subscribe(name, group="g", **fast())
    @broker.publisher(out)
    def handle(body):
        calls.append(1)

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: calls and pending(r, name) == 0)
    settle(0.2)
    assert r.xlen(out) == 0


def test_falsy_non_none_return_is_published(broker: Broker, r, name):
    out = f"{name}-out"

    @broker.subscribe(name, group="g", **fast())
    @broker.publisher(out)
    def handle(body):
        return 0

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: _out(r, out) == [0])


def test_stacked_publishers_publish_to_every_stream(broker: Broker, r, name):
    a, b = f"{name}-a", f"{name}-b"

    @broker.subscribe(name, group="g", **fast())
    @broker.publisher(a)
    @broker.publisher(b)
    def handle(body):
        return {"v": 1}

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: _out(r, a) == [{"v": 1}] and _out(r, b) == [{"v": 1}])


def test_chained_pipeline_between_two_handlers(broker: Broker, r, name):
    mid, final = f"{name}-mid", f"{name}-final"

    @broker.subscribe(name, group="g", **fast())
    @broker.publisher(mid)
    def first(body):
        return {"n": body["n"] + 1}

    @broker.subscribe(mid, group="g", **fast())
    @broker.publisher(final)
    def second(body):
        return {"n": body["n"] * 10}

    broker.start()
    broker.publish(name, {"n": 1})
    assert wait_until(lambda: _out(r, final) == [{"n": 20}])


def test_publisher_respects_maxlen(broker: Broker, r, name):
    out = f"{name}-out"

    @broker.subscribe(name, group="g", **fast())
    @broker.publisher(out, maxlen=10)
    def handle(body):
        return {"i": body["i"]}

    broker.start()
    for i in range(300):
        broker.publish(name, {"i": i})
    assert wait_until(lambda: pending(r, name) == 0 and read_count(r, name) == 300)
    assert r.xlen(out) < 300


def test_failing_handler_does_not_publish(broker: Broker, r, name):
    out = f"{name}-out"
    calls = []

    @broker.subscribe(name, group="g", max_retries=0, **fast())
    @broker.publisher(out)
    def handle(body):
        calls.append(1)
        raise ValueError("x")

    broker.start()
    broker.publish(name, {})
    assert wait_until(lambda: r.xlen(f"{name}-dlq") == 1)
    assert r.xlen(out) == 0
