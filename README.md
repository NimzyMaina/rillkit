# rillkit

Simple publish and consume for Redis Streams. Consumer groups, retries with backoff, a dead-letter
queue, ack policies, middleware and lifecycle hooks, without the boilerplate.

**Docs:** https://nimzymaina.github.io/rillkit/

```bash
pip install rillkit             # plain dict bodies
pip install "rillkit[pydantic]" # optional typed bodies
```

```python
from rillkit import Broker, Stream

orders = Stream("orders", group="workers")
broker = Broker.from_env()  # REDIS_URL, or REDIS_HOST / REDIS_PORT / REDIS_PASSWORD / REDIS_SSL


@broker.subscribe(orders, max_retries=3)
def handle(order: dict):
    print("got", order)


if __name__ == "__main__":
    broker.publish(orders, {"id": 1})
    broker.run()  # blocks; Ctrl-C / SIGTERM finishes the current message and exits
```

## Features

- Consumer groups: group creation, `XREADGROUP`, and `XAUTOCLAIM`-style takeover of stuck messages
- At-least-once delivery with retries (`max_retries`, optional exponential `backoff`)
- Dead-letter queue with the original id, error and delivery count; `broker.replay_dlq()`
- `AckPolicy`: `NACK_ON_ERROR` (default), `ACK_ALWAYS`, `ACK_FIRST`, `MANUAL`
- Plain dicts by default, Pydantic models when you annotate the handler with one
- Middleware hooks (`on_receive`, `consume_scope`, `publish_scope`, `after_processed`) and an `Idempotent` middleware
- `on_startup`, `after_startup`, `on_shutdown`, `after_shutdown` hooks and graceful SIGTERM shutdown
- Worker heartbeats: `broker.active_workers(stream)` includes idle workers
- Stack `@broker.publisher(...)` under `@broker.subscribe(...)` to publish a handler's return value
- The wire format is a single `data` field holding JSON, so plain redis-py producers interoperate

## Development

```bash
uv sync --group dev
REDIS_URL=redis://localhost:6379/15 uv run pytest   # needs a Redis
npm install && npm run docs:dev                     # docs
```

MIT licensed.
