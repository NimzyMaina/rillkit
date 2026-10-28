# Retries and the DLQ

## How many attempts?

`max_retries` is the number of **retries after the first attempt**. The total number of times your handler can run for one message is:

```text
total attempts = max_retries + 1
```

| `max_retries` | Handler runs at most |
| --- | --- |
| `0` | 1 time, a failure goes straight to the DLQ |
| `3` (default) | 4 times |
| `None` | forever, never dead-lettered (except decode errors) |

In this run `max_retries=2`, so the handler that always fails is called 3 times before it is dead-lettered. `msg.deliveries` counts the delivery you are in, starting at 1.

```python [retries_dlq.py]
import logging
import time

from rillkit import Broker, Message, Stream

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

broker = Broker("redis://localhost:6379/0")
JOBS = Stream("jobs", group="workers")
fixed = False


@broker.subscribe(JOBS, consumer="worker-1", max_retries=2, claim_idle_ms=300, block_ms=200)
def run_job(job: dict, msg: Message):
    print(f"job {job['name']!r}: delivery {msg.deliveries}")
    if job["name"] == "flaky" and msg.deliveries < 3:
        raise ConnectionError("upstream timed out")
    if job["name"] == "broken" and not fixed:
        raise ValueError("bad input")


broker.start()
broker.publish(JOBS, {"name": "ok"})
broker.publish(JOBS, {"name": "flaky"})
broker.publish(JOBS, {"name": "broken"})
time.sleep(4)

print("--- DLQ ---")
for entry_id, fields in broker.client.xrange("jobs-dlq"):
    for k, v in fields.items():
        print(f"{k.decode():14} {v.decode()}")

print("--- replay after the fix ---")
fixed = True
print("replayed:", broker.replay_dlq(JOBS))
time.sleep(1)
print("DLQ length:", broker.client.xlen("jobs-dlq"))
broker.stop()
```

```text
INFO consumer started | stream: jobs | group: workers | consumer: worker-1 | policy: nack_on_error | max retries: 2
job 'ok': delivery 1
job 'flaky': delivery 1
ERROR handler failed for message 1793094996790-1 (delivery 1): upstream timed out
job 'broken': delivery 1
ERROR handler failed for message 1793094996790-2 (delivery 1): bad input
job 'flaky': delivery 2
ERROR handler failed for message 1793094996790-1 (delivery 2): upstream timed out
job 'broken': delivery 2
ERROR handler failed for message 1793094996790-2 (delivery 2): bad input
job 'flaky': delivery 3
job 'broken': delivery 3
ERROR handler failed for message 1793094996790-2 (delivery 3): bad input
WARNING moving message 1793094996790-2 to jobs-dlq: bad input
--- DLQ ---
data           {"name": "broken"}
x-original-id  1793094996790-2
x-stream       jobs
x-group        workers
x-error        bad input
x-deliveries   3
--- replay after the fix ---
job 'broken': delivery 1
replayed: 1
DLQ length: 0
INFO consumer stopped | stream: jobs | consumer: worker-1
```

## claim_idle_ms must exceed your slowest handler

A failed message becomes eligible for retry once it has been pending and **idle** for `claim_idle_ms`. RillKit cannot tell "failed" from "still running on another worker" using idleness alone, so:

::: danger Set claim_idle_ms longer than the longest handler runtime
If your handler can take 90 seconds and `claim_idle_ms` is the default 60 seconds, another worker will claim the message while the first is still working, and both will process it. Choose a value comfortably above the worst case, for example twice the longest run.
:::

Remember that a message is also retried only when a consumer gets around to the claim step, which happens at the top of each loop. With a long `block_ms`, a retry can start up to `block_ms` late. Lower `block_ms` if you need prompt retries.

## Backoff

Each retry waits longer than the last:

```text
required idle = min(claim_idle_ms * backoff ** (deliveries - 1), max_backoff_ms)
```

With `claim_idle_ms=300`, `backoff=2.0` and an always-failing handler:

```python [g_backoff.py]
import logging
import time

from rillkit import Broker, Message, Stream

logging.basicConfig(level=logging.CRITICAL)
broker = Broker("redis://localhost:6379/0")
t0 = time.time()


@broker.subscribe(Stream("tasks", group="g"), consumer="c1", block_ms=100,
                  max_retries=3, claim_idle_ms=300, backoff=2.0)
def always(task: dict, msg: Message):
    print(f"delivery {msg.deliveries} at t={time.time() - t0:.1f}s")
    raise RuntimeError("no")


broker.start()
broker.publish("tasks", {"n": 1})
time.sleep(4)
broker.stop()
```

```text
delivery 1 at t=0.0s
delivery 2 at t=0.4s
delivery 3 at t=1.0s
delivery 4 at t=2.2s
```

The gaps between deliveries are 0.3 s, 0.6 s and 1.2 s. The default `backoff=1.0` keeps them constant, and `max_backoff_ms` (default 15 minutes) caps the growth.

## The dead letter queue

When retries run out, RillKit appends a copy of the entry to the DLQ stream and acknowledges the original so it stops coming back. The DLQ is a normal stream named `<stream>-dlq` unless you set `Stream(..., dlq="my-dead-letters")`.

The copy contains the original fields (including `data`) plus:

| Field | Value |
| --- | --- |
| `x-original-id` | the entry id in the original stream |
| `x-stream` | the original stream name |
| `x-group` | the consumer group that gave up |
| `x-error` | the error message, cut to 1000 characters |
| `x-deliveries` | how many times the entry was delivered |

You can inspect it with plain Redis commands:

```bash
redis-cli XRANGE orders-dlq - +
```

Nothing consumes the DLQ for you. Look at it, fix the cause, then replay.

## replay_dlq

```python
moved = broker.replay_dlq("orders", count=100)
```

`replay_dlq` takes the **original** stream (or `Stream`), not the DLQ name. It moves up to `count` entries from the DLQ back onto the stream as brand-new entries, dropping the `x-` fields, and deletes them from the DLQ. It returns how many moved. The replayed messages go through all the normal rules again, including a fresh set of retries. Replays get new entry ids; the old id survives only in the log you kept.

The last part of the run above shows it: after setting `fixed = True`, `replay_dlq` moved the broken job, the handler succeeded on delivery 1, and the DLQ is empty.

## Decode errors skip retries

If a message cannot be decoded, retrying cannot help, so RillKit dead-letters it on the first delivery. That covers:

- no `data` field
- `data` that is not valid JSON
- a pydantic model that fails validation (see [Pydantic models](/guide/pydantic))

```python [g_decode.py]
import logging
import time

import redis

from rillkit import Broker, Stream

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
URL = "redis://localhost:6379/0"
broker = Broker(URL)


@broker.subscribe(Stream("tasks", group="g"), consumer="c1", block_ms=200)
def handle(task: dict):
    print("ok", task)


r = redis.Redis.from_url(URL, decode_responses=True)
r.xadd("tasks", {"data": "this is not json"})
r.xadd("tasks", {"other": "no data field"})
broker.start()
time.sleep(1)
for _id, f in r.xrange("tasks-dlq"):
    print({k: v for k, v in f.items() if k in ("data", "other", "x-error", "x-deliveries")})
broker.stop()
```

```text
ERROR message 1793095027094-0 cannot be decoded, sending to DLQ: body is not valid JSON: Expecting value: line 1 column 1 (char 0)
WARNING moving message 1793095027094-0 to tasks-dlq: body is not valid JSON: Expecting value: line 1 column 1 (char 0)
ERROR message 1793095027095-0 cannot be decoded, sending to DLQ: entry has no 'data' field
WARNING moving message 1793095027095-0 to tasks-dlq: entry has no 'data' field
{'data': 'this is not json', 'x-error': 'body is not valid JSON: Expecting value: line 1 column 1 (char 0)', 'x-deliveries': '1'}
{'other': 'no data field', 'x-error': "entry has no 'data' field", 'x-deliveries': '1'}
```

Both entries went to the DLQ with `x-deliveries` of `1`, regardless of `max_retries`.

## Also dead-lettered, quietly

When a message was already pending (for instance after a worker crash) and has been delivered more than `max_retries` times, RillKit dead-letters it as it is claimed, with `x-error` set to `retries exhausted`, without calling the handler again.

## Skipping retries

Some messages can never succeed, so retrying them only wastes attempts. Call `msg.reject("reason")` or `raise RejectMessage("reason")` and the message goes to the DLQ as soon as the handler finishes, with `x-deliveries` unchanged and `reason` in `x-error`. Decode and validation failures take the same path automatically. `nack` is the opposite: "try again later".
