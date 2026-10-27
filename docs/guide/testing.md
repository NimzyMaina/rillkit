# Testing

## Handlers are plain functions

`@broker.subscribe` returns your function unchanged, and `@broker.publisher` only records where its return value should go. So the cheapest tests call the handler directly with no Redis at all:

```python
def test_handler_is_a_plain_function():
    assert handle_order({"id": 7, "total": 100}) == {"order_id": 7, "amount": 116.0}
```

If your handler takes a `Message`, build a stand-in. Anything with the attributes you use will do, for example `types.SimpleNamespace(id="1-0", deliveries=1, body={...})`.

## Against a real Redis

For end-to-end checks, start a real `Broker`, register your handler on a **unique stream per test**, and wait for the result. Unique names keep tests independent of each other and of leftovers from previous runs.

```python [tests/conftest.py]
import time
import uuid

import pytest
import redis

from rillkit import Broker, Stream

REDIS_URL = "redis://localhost:6379/0"


@pytest.fixture
def redis_client():
    client = redis.Redis.from_url(REDIS_URL)
    yield client
    client.close()


@pytest.fixture
def stream(redis_client):
    """A stream with a unique name so tests never see each other's messages."""
    name = f"test-{uuid.uuid4().hex[:8]}"
    yield Stream(name, group="test")
    redis_client.delete(name, f"{name}-dlq")


@pytest.fixture
def broker():
    b = Broker(REDIS_URL)
    yield b
    b.stop()


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False
```

Then the tests:

```python [tests/app.py]
from rillkit import Broker, Stream

broker = Broker.from_env()


@broker.subscribe(Stream("orders", group="billing"))
@broker.publisher("invoices")
def handle_order(order: dict) -> dict:
    return {"order_id": order["id"], "amount": round(order["total"] * 1.16, 2)}
```

```python [tests/test_orders.py]
from app import handle_order
from conftest import wait_for


def test_handler_is_a_plain_function():
    assert handle_order({"id": 7, "total": 100}) == {"order_id": 7, "amount": 116.0}


def test_end_to_end(broker, stream, redis_client):
    results = []

    @broker.subscribe(stream, block_ms=100)
    def handle(order: dict):
        results.append(order["id"])

    broker.start()
    broker.publish(stream, {"id": 1})
    assert wait_for(lambda: results == [1])


def test_failures_land_in_the_dlq(broker, stream, redis_client):
    @broker.subscribe(stream, block_ms=100, max_retries=0)
    def handle(order: dict):
        raise ValueError("boom")

    broker.start()
    broker.publish(stream, {"id": 1})
    assert wait_for(lambda: redis_client.xlen(stream.dlq_name) == 1)
    (_, fields), = redis_client.xrange(stream.dlq_name)
    assert fields[b"x-error"] == b"boom"
```

Run with `pytest -v`:

```text
test_orders.py::test_handler_is_a_plain_function PASSED                  [ 33%]
test_orders.py::test_end_to_end PASSED                                   [ 66%]
test_orders.py::test_failures_land_in_the_dlq PASSED                     [100%]
============================== 3 passed in 0.4s ===============================
```

Tips:

- Use a short `block_ms` (100 or so) so `stop()` returns fast. The `broker` fixture stops the broker at the end of each test.
- Use `max_retries=0` to test the DLQ without waiting. To test retries, also set a small `claim_idle_ms` (a few hundred milliseconds).
- Poll for outcomes with a deadline, as `wait_for` does, rather than `time.sleep` with a guess.
- Register the same handler on a fresh `Broker` per test (`broker.subscribe(stream)(handle_order)`). The module-level broker in your app never needs to start.
- Use a dedicated database number (for instance `redis://localhost:6379/15`) for tests, and never `FLUSHALL`. Deleting your own unique keys in the fixture is enough.
