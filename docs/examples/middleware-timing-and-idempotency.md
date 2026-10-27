# Timing and idempotency middleware

Two middlewares on one broker: a custom `Timing` that reports how long each message took, and the built-in `Idempotent` that skips duplicates by a business key.

```python [middleware_timing.py]
import logging
import time

from rillkit import BaseMiddleware, Broker, Idempotent, Message, Stream

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


class Timing(BaseMiddleware):
    """Log how long each message took, whether it worked or not."""

    def on_receive(self, msg: Message) -> None:
        msg.started = time.perf_counter()  # per-message state lives on the Message

    def after_processed(self, msg: Message, exc) -> None:
        ms = (time.perf_counter() - msg.started) * 1000
        status = "failed" if exc else "ok"
        print(f"timing {msg.stream.name} {msg.id} {status} in {ms:.0f} ms")


broker = Broker(
    "redis://localhost:6379/0",
    middlewares=[
        Timing(),
        Idempotent(key=lambda m: m.body["request_id"], ttl=3600),
    ],
)
PAYMENTS = Stream("payments", group="ledger")


@broker.subscribe(PAYMENTS, consumer="ledger-1", block_ms=300)
def charge(payment: dict):
    time.sleep(0.05)
    print(f"charging {payment['amount']} (request {payment['request_id']})")


broker.start()
broker.publish(PAYMENTS, {"request_id": "r-1", "amount": 100})
broker.publish(PAYMENTS, {"request_id": "r-2", "amount": 250})
broker.publish(PAYMENTS, {"request_id": "r-1", "amount": 100})  # a duplicate, e.g. a client retry
time.sleep(1.5)
broker.stop()
```

Output:

```text
INFO consumer started | stream: payments | group: ledger | consumer: ledger-1 | policy: nack_on_error | max retries: 3
charging 100 (request r-1)
timing payments 1793095005101-0 ok in 51 ms
charging 250 (request r-2)
timing payments 1793095005102-0 ok in 54 ms
timing payments 1793095005102-1 ok in 0 ms
INFO consumer stopped | stream: payments | consumer: ledger-1
```

- The producer published request `r-1` twice, as a client retry might. The handler ran once for it. The duplicate was acknowledged by `Idempotent` (the last `timing` line, `1 ms`, never reached the handler).
- `Timing` is first in the list, so it is outermost: its clock covers `Idempotent` and the handler. It records in `on_receive` and reports in `after_processed`, which runs even when the handler fails.
- The start time is stored on the `Message` (`msg.started`), not on `self`, because one middleware instance serves every message.

See [Middleware](/guide/middleware) for ordering and the other hooks.
