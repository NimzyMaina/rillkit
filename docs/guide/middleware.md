# Middleware

Middleware lets you add behaviour around every message without touching handlers: logging, metrics, tracing, deduplication, authentication, publishing rules.

You write a subclass of `BaseMiddleware` and override any of four hooks:

| Hook | Runs | Typical use |
| --- | --- | --- |
| `on_receive(msg)` | first, before decoding | start a timer, bind log context |
| `consume_scope(call_next, msg)` | wraps decoding and the handler | skip, short-circuit, catch errors, set state |
| `publish_scope(call_next, cmd)` | wraps every publish | stamp metadata, count, block |
| `after_processed(msg, exc)` | always last, even after failures | record metrics and timings |

Attach middleware in any of these ways:

```python
broker = Broker(url, middlewares=[Timing(), Idempotent(key=...)])  # for every subscriber
broker.use(Timing())                                               # same, after construction

@broker.subscribe(stream, middlewares=[RateLimit()])               # this subscriber only
def handle(...): ...
```

`self.broker` is set automatically, so a middleware can reach `self.broker.client`.

## Ordering

Broker-wide middleware is outermost, then the subscriber's own. Within a list, the **first is outermost**.

- `on_receive` and `after_processed` run in list order.
- `consume_scope` nests: the first middleware's scope opens first and closes last.
- `publish_scope` nests the same way, but only for broker-wide middleware. A middleware passed to `subscribe(middlewares=...)` does not see publishes.

```python [g_middleware.py]
import logging
import time

from rillkit import BaseMiddleware, Broker, Message, PublishCommand, Stream

logging.basicConfig(level=logging.WARNING)


class Tracer(BaseMiddleware):
    def __init__(self, name):
        self.name = name

    def on_receive(self, msg):
        print(f"{self.name}.on_receive")

    def consume_scope(self, call_next, msg):
        print(f"{self.name}.consume_scope enter")
        try:
            return call_next(msg)
        finally:
            print(f"{self.name}.consume_scope exit")

    def publish_scope(self, call_next, cmd):
        print(f"{self.name}.publish_scope enter ({cmd.stream.name})")
        return call_next(cmd)

    def after_processed(self, msg, exc):
        print(f"{self.name}.after_processed exc={exc!r}")


class AddTraceId(BaseMiddleware):
    """Stamp every published dict with a trace id."""

    def publish_scope(self, call_next, cmd: PublishCommand):
        if isinstance(cmd.body, dict):
            cmd.body = {**cmd.body, "trace_id": "t-123"}
        return call_next(cmd)


broker = Broker("redis://localhost:6379/0", middlewares=[Tracer("A"), AddTraceId()])


@broker.subscribe(Stream("tasks", group="g"), consumer="c1", block_ms=200, middlewares=[Tracer("B")])
def handle(task: dict):
    print("handler", task)


broker.start()
broker.publish("tasks", {"n": 1})
time.sleep(1)
broker.stop()
```

```text
A.publish_scope enter (tasks)
A.on_receive
B.on_receive
A.consume_scope enter
B.consume_scope enter
handler {'n': 1, 'trace_id': 't-123'}
B.consume_scope exit
A.consume_scope exit
A.after_processed exc=None
B.after_processed exc=None
```

`A` is on the broker and `B` only on the subscriber, so `A` wraps `B`. The trace id added by `AddTraceId` is visible in the handler. Notice that `AddTraceId` mutated `cmd.body`, which is how you change what gets published.

## Rules of thumb

- **One instance is shared by every message** and runs on the consumer thread (or on whichever thread publishes). Keep per-message state on the `Message` object, as in `msg.started = ...`, not on `self`.
- Call `call_next(msg)` exactly once in `consume_scope` and return its result, unless you mean to skip the handler.
- Raise `AckMessage`, `NackMessage` or `RejectMessage` from `on_receive` or `consume_scope` to short-circuit. Any other exception from `on_receive` or `consume_scope` is treated like a handler failure.
- `after_processed` failures are logged and swallowed, so a broken metrics backend cannot break message handling. It runs after the ack/nack/DLQ decision has been made, so `msg.acked` and `msg.nacked` are final.
- `exc` in `after_processed` is the error that caused a failure, or `None` after a clean run or an `AckMessage`.
- `msg.body` can be read in `consume_scope` before calling `call_next`. If it cannot be decoded, that raises `DecodeError` and the message is dead-lettered.

## Idempotent

Redis delivers **at least once**: a worker that crashes after finishing but before acking will see the message again. `Idempotent` makes reprocessing a no-op:

```python
from rillkit import Broker, Idempotent

broker = Broker(url, middlewares=[Idempotent(key=lambda m: m.body["request_id"])])
```

| Parameter | Default | Meaning |
| --- | --- | --- |
| `key` | required | `Callable[[Message], str]` returning the idempotency key |
| `ttl` | `604800` (7 days) | seconds the "done" marker is kept |
| `prefix` | `"rillkit:done:"` | Redis key prefix; the full key is `<prefix><stream name>:<key>` |

When the key already exists, the middleware raises `AckMessage`, so the duplicate is acknowledged without running the handler. The marker is written only **after** the handler returns without raising, so failed attempts are still retried.

::: warning What it does not guarantee
It is not exactly-once. If a crash lands between the handler's side effects and the marker being written, the work repeats. Two workers handling the same key at the same moment can both run it. Keep your side effects idempotent where you can, and treat `Idempotent` as a strong deduplicator rather than a lock.
:::

## Writing your own

A timing middleware and `Idempotent` working together, from the [timing and idempotency example](/examples/middleware-timing-and-idempotency):

```python
class Timing(BaseMiddleware):
    def on_receive(self, msg: Message) -> None:
        msg.started = time.perf_counter()

    def after_processed(self, msg: Message, exc) -> None:
        ms = (time.perf_counter() - msg.started) * 1000
        print(f"{msg.stream.name} {msg.id} {'failed' if exc else 'ok'} in {ms:.0f} ms")
```

A logging middleware that adds context to every failure, and a metrics one that counts outcomes:

```python
import logging
from collections import Counter

log = logging.getLogger("myapp")


class Logging(BaseMiddleware):
    def consume_scope(self, call_next, msg):
        try:
            return call_next(msg)
        except Exception:
            log.exception("failed %s delivery=%s consumer=%s", msg.id, msg.deliveries, msg.consumer)
            raise  # re-raise so rillkit still retries


class Metrics(BaseMiddleware):
    def __init__(self):
        self.outcomes = Counter()

    def after_processed(self, msg, exc):
        self.outcomes[("failed" if exc else "ok", msg.stream.name)] += 1
```

Always re-raise in `consume_scope` if you catch an exception and still want rillkit to retry. Swallowing it makes the message look successful.

## publish_scope

`publish_scope(call_next, cmd)` receives a [`PublishCommand`](/reference/middleware#publishcommand) with `stream`, `body` and `maxlen`. Mutate it to change what is published, call `call_next(cmd)` to write the entry and return the new id, or raise to veto the publish. It wraps both direct `broker.publish(...)` calls and values returned from `@broker.publisher` handlers.
