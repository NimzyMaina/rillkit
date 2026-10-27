# Retries and DLQ

Three jobs: one that works, one that fails twice then succeeds (a flaky upstream), and one that never works until we fix a bug. The timings are shortened (`claim_idle_ms=300`, `block_ms=200`) so you can watch it in a few seconds.

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

Output:

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

Walk through it:

- `ok` ran once and was acknowledged.
- `flaky` failed on deliveries 1 and 2 and succeeded on delivery 3, which is the last one allowed (`max_retries=2` allows 3 attempts), so it was never dead-lettered.
- `broken` failed on all 3 attempts, so rillkit logged `moving message ... to jobs-dlq` and copied it to `jobs-dlq` with the `x-` context fields.
- After "fixing" the bug, `replay_dlq(JOBS)` moved the entry back onto `jobs` and the handler processed it on delivery 1 of the new entry. The DLQ is empty again.

Read the full rules in [Retries and the DLQ](/guide/retries-and-dlq). In production keep the default `claim_idle_ms=60000`, or anything longer than your slowest handler.
