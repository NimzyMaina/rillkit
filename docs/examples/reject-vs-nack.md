# Reject vs nack

Two ways to say "this message did not work", with opposite outcomes:

| | Retried? | Ends up | Use it when |
|---|---|---|---|
| `msg.nack()` / `raise NackMessage()` | Yes, up to `max_retries` more times | Pending, then the DLQ if retries run out | The failure may be temporary: a timeout, a rate limit, a dependency that is down |
| `msg.reject(reason)` / `raise RejectMessage(reason)` | No | The DLQ right away, with `reason` as `x-error` | The message can never succeed: bad input, unknown customer, unsupported version |

```python
import logging
import time

from rillkit import Broker, Message, RejectMessage, Stream

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

broker = Broker("redis://localhost:6379/0")
broker.client.delete("signups", "signups-dlq")
signups = Stream("signups", group="workers")
attempts = {}


@broker.subscribe(signups, consumer="w1", max_retries=2, claim_idle_ms=200, block_ms=100)
def handle(signup: dict, msg: Message):
    email = signup["email"]
    attempts[email] = attempts.get(email, 0) + 1

    if "@" not in email:
        # can never succeed: retrying is pointless
        raise RejectMessage("not an email address")

    if email.endswith("@flaky.test"):
        # might work later: let rillkit retry it
        msg.nack()
        return


broker.start()
for email in ["ada@example.com", "not-an-email", "bob@flaky.test"]:
    broker.publish(signups, {"email": email})

time.sleep(2.5)
broker.stop()

for email, n in attempts.items():
    print(f"{email:<16} handler ran {n}x")
print()
for _, fields in broker.client.xrange("signups-dlq"):
    print(
        f"{fields[b'data'].decode():<32} deliveries={fields[b'x-deliveries'].decode()} "
        f"error={fields[b'x-error'].decode()!r}"
    )
broker.client.delete("signups", "signups-dlq")
```

Output:

```text
WARNING moving message 1793098223460-0 to signups-dlq: not an email address
WARNING moving message 1793098223461-0 to signups-dlq: nacked
ada@example.com  handler ran 1x
not-an-email     handler ran 1x
bob@flaky.test   handler ran 3x

{"email": "not-an-email"}        deliveries=1 error='not an email address'
{"email": "bob@flaky.test"}      deliveries=3 error='nacked'
```

- `ada@example.com` returned normally, so it was acked.
- `not-an-email` was rejected on its first delivery: one handler run, `x-deliveries=1`, and your reason in `x-error`.
- `bob@flaky.test` was nacked every time. With `max_retries=2` that is the first try plus two retries, so three runs, and then it was dead-lettered.

::: tip Both work under every policy
`reject` also works with `ACK_FIRST`, `ACK_ALWAYS` and `MANUAL`. If a handler calls `msg.reject()` and then raises, the reject still wins. See [Ack policies](/guide/ack-policies) and [Retries and the DLQ](/guide/retries-and-dlq).
:::

Fix the cause, then send rejected messages back with [`broker.replay_dlq()`](/reference/broker).
