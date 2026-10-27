# Ack policies

An **ack policy** decides what rillkit does with a message when your handler finishes. Pass it to `subscribe`:

```python
from rillkit import AckPolicy

@broker.subscribe(stream, ack_policy=AckPolicy.ACK_ALWAYS)
def handle(job: dict): ...
```

## The four policies

| Policy | On success | On exception | Retried? | Delivery guarantee |
| --- | --- | --- | --- | --- |
| `NACK_ON_ERROR` (default) | acked when the handler returns | left pending, retried, then DLQ | yes | at least once |
| `ACK_ALWAYS` | acked when the handler returns | acked anyway, error is logged | never | at most once for failures |
| `ACK_FIRST` | acked **before** the handler runs | already acked, error is logged | never | at most once |
| `MANUAL` | rillkit does nothing; you call `msg.ack()` | left pending (same as a nack), retried, then DLQ | yes | what you implement |

Here is each policy handling a handler that always raises, with `max_retries=1`:

```python [g_acks.py]
import logging
import time

from rillkit import AckMessage, AckPolicy, Broker, NackMessage, Stream

logging.basicConfig(level=logging.CRITICAL)
URL = "redis://localhost:6379/0"

for policy in AckPolicy:
    broker = Broker(URL)
    calls = []
    name = "tasks"
    broker.client.delete(name, name + "-dlq")

    @broker.subscribe(Stream(name, group="g"), ack_policy=policy, max_retries=1, claim_idle_ms=200, block_ms=100,
                      consumer="c1")
    def fail(task: dict):
        calls.append(1)
        raise RuntimeError("boom")

    broker.start()
    broker.publish(name, {"x": 1})
    time.sleep(1.5)
    pending = broker.client.xpending(name, "g")["pending"]
    dlq = broker.client.xlen(name + "-dlq")
    broker.stop()
    print(f"{policy.value:14} handler calls={len(calls)} pending={pending} dlq={dlq}")
    # note: stream key left over; cleaned by the runner next time
    import redis
    redis.Redis.from_url(URL).delete(name, name + "-dlq")
```

```text
nack_on_error  handler calls=2 pending=0 dlq=1
ack_always     handler calls=1 pending=0 dlq=0
ack_first      handler calls=1 pending=0 dlq=0
manual         handler calls=2 pending=0 dlq=1
```

- `nack_on_error` ran the handler twice (the first try plus one retry), then dead-lettered it.
- `ack_always` and `ack_first` ran it once and dropped it. Use these when losing a message is cheaper than reprocessing it (metrics, cache warming).
- `manual` still nacks when the handler raises. Only the success path is left to you.

::: warning ACK_FIRST loses work on a crash
With `ACK_FIRST` the entry is gone from the pending list before your code starts. If the process dies halfway through, the message is lost forever.
:::

## ack and nack

Every handler that takes a `Message` can call:

- `msg.ack()` removes the entry from the pending list immediately (an `XACK`). It is safe to call twice.
- `msg.nack()` marks the message as failed without raising. It stays pending and is retried after `claim_idle_ms`, or dead-lettered if retries are used up. It has no effect after an ack.

`msg.acked` and `msg.nacked` tell you the current state.

Under `NACK_ON_ERROR` and `ACK_ALWAYS` you can use them too. If you call `msg.nack()` and then return normally, rillkit sees the nack and does not ack on your behalf.

## AckMessage and NackMessage

Sometimes the simplest way to leave a handler is to raise. rillkit provides two control-flow exceptions that work from the handler **and from middleware**:

- `raise AckMessage()` acknowledges the message and stops processing. Not an error; nothing is logged as a failure.
- `raise NackMessage()` nacks the message so it is retried (or dead-lettered if retries are used up).

```python [g_acks2.py]
import logging
import time

from rillkit import AckMessage, Broker, Message, NackMessage, Stream

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
broker = Broker("redis://localhost:6379/0")
calls = []


@broker.subscribe(Stream("tasks", group="g"), consumer="c1", max_retries=1, claim_idle_ms=200, block_ms=100)
def handle(task: dict, msg: Message):
    calls.append((task["kind"], msg.deliveries))
    if task["kind"] == "stale":
        raise AckMessage()            # done, nothing to do, do not retry
    if task["kind"] == "busy":
        raise NackMessage()           # not now, retry later
    print("processed", task)


broker.start()
for kind in ("ok", "stale", "busy"):
    broker.publish("tasks", {"kind": kind})
time.sleep(2)
print(calls)
print("dlq:", [f[b"x-error"].decode() for _, f in broker.client.xrange("tasks-dlq")])
broker.stop()
```

```text
INFO consumer started | stream: tasks | group: g | consumer: c1 | policy: nack_on_error | max retries: 1
processed {'kind': 'ok'}
WARNING moving message 1793095021800-0 to tasks-dlq: 
[('ok', 1), ('stale', 1), ('busy', 1), ('busy', 2)]
dlq: ['']
INFO consumer stopped | stream: tasks | consumer: c1
```

`stale` was acknowledged on its first delivery. `busy` was nacked, retried once, and then dead-lettered because `max_retries=1`.

::: tip Give `NackMessage` a reason
The DLQ entry's `x-error` field is `str(exception)`. `NackMessage()` has an empty message, so the DLQ shows an empty error, as above. Use `raise NackMessage("rate limited")` to leave a useful trace.
:::

## MANUAL in practice

Use `MANUAL` when the work finishes somewhere other than the handler's return, for example when you hand the message to a thread pool and ack from there:

```python
@broker.subscribe(stream, ack_policy=AckPolicy.MANUAL)
def handle(job: dict, msg: Message):
    if not valid(job):
        msg.ack()          # poison: drop it, retrying will not help
        return
    if not upstream_ready():
        msg.nack()         # try again later
        return
    do_work(job)
    msg.ack()              # only now is the work really done
```

If a `MANUAL` handler returns without calling either, the message stays pending, is claimed after `claim_idle_ms`, and counts as another delivery. That is almost never what you want, so make sure every code path ends in `ack()` or `nack()`. A full version is in the [manual ack example](/examples/manual-ack).
