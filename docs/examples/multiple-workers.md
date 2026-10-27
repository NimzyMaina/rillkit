# Multiple workers

Several consumers in one group share the stream. Here three workers (each with its own `Broker`, as separate processes would have) share 30 tasks, and `active_workers` shows who is alive.

```python [multiple_workers.py]
import collections
import logging
import threading
import time

from rillkit import Broker, Message, Stream

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

URL = "redis://localhost:6379/0"
TASKS = Stream("tasks", group="workers")
handled = collections.Counter()
lock = threading.Lock()


def make_worker(name: str) -> Broker:
    broker = Broker(URL)

    @broker.subscribe(TASKS, consumer=name, count=2, block_ms=200)
    def work(task: dict, msg: Message):
        time.sleep(0.05)
        with lock:
            handled[msg.consumer] += 1

    return broker


workers = [make_worker(f"worker-{i}") for i in (1, 2, 3)]
for w in workers:
    w.start()

for i in range(30):
    workers[0].publish(TASKS, {"n": i})
time.sleep(0.5)
print("active workers:", workers[0].active_workers(TASKS))
time.sleep(2)

print("handled per consumer:", dict(sorted(handled.items())), "total:", sum(handled.values()))
for w in workers:
    w.stop()
```

Output:

```text
active workers: ['worker-1', 'worker-2', 'worker-3']
handled per consumer: {'worker-1': 9, 'worker-2': 11, 'worker-3': 10} total: 30
```

- Each `Broker` has its own Redis connection and its own consumer name (`worker-1` to `worker-3`).
- Every task was handled: the total is 30. The split between workers varies from run to run.
- `active_workers` listed all three, from their heartbeats, even though they had not all received a message yet.

In production, run this as separate processes or containers. Give each a unique `consumer` name, or rely on the default `<group>-<hostname>-<pid>`. See [Operations](/guide/operations#scaling).
