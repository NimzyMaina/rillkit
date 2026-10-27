# Publishing

## `Broker.publish`

```python
entry_id = broker.publish(stream, body, maxlen=None)
```

`stream` is either a plain name or a [`Stream`](/reference/stream). `body` is anything the codec can encode: by default JSON-serialisable values, or a pydantic model. It returns the new entry id as a `str`.

```python [g_publishing.py]
from rillkit import Broker, PublishError, Stream

broker = Broker("redis://localhost:6379/0")

entry_id = broker.publish("events", {"type": "signup", "user": 42})
print("entry id:", entry_id)

# keep roughly the last 1000 entries
EVENTS = Stream("events", maxlen=1000)
broker.publish(EVENTS, {"type": "login"})
broker.publish(EVENTS, {"type": "login"}, maxlen=500)  # per-call override
print("length:", broker.client.xlen("events"))

# publisher objects
audit = broker.publisher("events")
print("via publisher:", audit.publish({"type": "audit"}))

# stacking: one return value, two streams
@broker.subscribe(Stream("orders", group="billing"))
@broker.publisher("events")
@broker.publisher("notifications")
def handle(order: dict) -> dict:
    return {"order": order["id"], "status": "billed"}

# call the handler directly (it is returned unchanged) to see what is attached
print([p.stream.name for p in handle._rillkit_publishers])

# failures
down = Broker("redis://localhost:1/0")
try:
    down.publish("events", {"x": 1})
except PublishError as e:
    print("PublishError:", e)
```

```text
entry id: 1793095014218-0
length: 3
via publisher: 1793095014220-0
['notifications', 'events']
PublishError: could not publish to events: Error 61 connecting to localhost:1. Connection refused.
```

`length: 3` counts the three `publish` calls made before it. The last line shows a failed publish: nothing is listening on port 1.

## Streams as shared definitions

`Stream` is a small frozen dataclass. Define it once and import it from both the producer and the consumer so the names cannot drift apart:

```python
# streams.py
from rillkit import Stream

ORDERS = Stream("orders", group="billing", maxlen=100_000)
```

`publish` only uses the name, `maxlen` and codec. A consumer also needs the `group`. See [Consuming](/guide/consuming).

## Capping the stream with `maxlen`

A stream grows forever unless you trim it. Set `maxlen` on the `Stream`, or pass `maxlen=` to a single `publish` call (the call wins). rillkit uses approximate trimming (`XADD ... MAXLEN ~ n`), which is cheap but may keep slightly more than `n` entries. Redis trims in whole blocks, so streams under about 100 entries are effectively never trimmed. Pass `approximate=False` to `publish` for an exact cap (slower on very large streams).

::: warning Trimming can drop unprocessed messages
If consumers fall further behind than `maxlen` entries, the oldest entries are deleted before anyone reads them. Choose a cap comfortably larger than your worst-case backlog. If an entry that is still pending gets trimmed, rillkit notices when it tries to claim it and simply acknowledges it.
:::

## The `publisher` decorator

`broker.publisher(stream)` returns a `Publisher`. As a decorator it publishes the **return value** of a handler (when it is not `None`):

```python
@broker.subscribe(Stream("orders", group="billing"))
@broker.publisher("invoices")
def handle(order: dict) -> dict:
    return {"order_id": order["id"], "amount": order["total"]}
```

- Returning `None` publishes nothing, so a handler can decide per message.
- Decorators **stack**: each `@broker.publisher(...)` adds another destination, and the same value goes to all of them.
- Order relative to `@broker.subscribe` does not matter, because `subscribe` returns your function unchanged.
- The publish happens inside the handler call. If a publish raises `PublishError`, the handler is treated as failed and the message is retried. Publishers that already ran for that attempt will publish again, so downstream consumers should tolerate duplicates.
- The decorated function is still a plain function. Calling it yourself returns the value and publishes nothing, which keeps tests simple.
- A `Publisher` can also be called directly: `broker.publisher("invoices", maxlen=10_000).publish({...})`.

## Errors: `PublishError`

If Redis is down, or the body cannot be encoded, `publish` raises [`PublishError`](/reference/exceptions) with the original error chained as `__cause__`:

```python
from rillkit import PublishError

try:
    broker.publish("events", {"type": "signup"})
except PublishError:
    ...  # retry, buffer locally, or return a 503 to your caller
```

::: tip What is not a `PublishError`
rillkit encodes with `json.dumps(body, default=str)`, so unusual objects (dates, UUIDs, decimals, dataclasses) are turned into strings instead of raising. If you need exact control, convert the data yourself or use a pydantic model.
:::
