# Lifecycle

## Startup and shutdown order

`broker.start()` and `broker.stop()` run your hooks around rillkit's own work:

| Step | When |
| --- | --- |
| 1. `@broker.on_startup` hooks | first, before anything touches Redis |
| 2. `PING` | checks the connection, raises if Redis is unreachable |
| 3. create consumer groups | `XGROUP CREATE ... MKSTREAM` for each subscriber |
| 4. start consumer threads | one daemon thread per subscriber |
| 5. `@broker.after_startup` hooks | groups exist and consumers are running |
| | *... messages flow ...* |
| 6. stop consumers | each finishes its current message and exits |
| 7. `@broker.on_shutdown` hooks | consumers are done; the Redis client is still open |
| 8. close the Redis client | |
| 9. `@broker.after_shutdown` hooks | the client is closed |

```python [g_lifecycle.py]
import logging
import time

from rillkit import Broker, Stream

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
broker = Broker("redis://localhost:6379/0")


@broker.on_startup
def before_connect():
    print("1. on_startup: nothing connected yet")


@broker.after_startup
def ready():
    print("2. after_startup: groups exist, consumers are running")


@broker.on_shutdown
def drain():
    print("3. on_shutdown: consumers finished, client still open:", broker.client.ping())


@broker.after_shutdown
def goodbye():
    print("4. after_shutdown: client closed")


@broker.subscribe(Stream("tasks", group="g"), consumer="c1", block_ms=200)
def handle(task: dict):
    pass


broker.start()
time.sleep(0.5)
broker.stop()
```

```text
1. on_startup: nothing connected yet
INFO consumer started | stream: tasks | group: g | consumer: c1 | policy: nack_on_error | max retries: 3
2. after_startup: groups exist, consumers are running
INFO consumer stopped | stream: tasks | consumer: c1
3. on_shutdown: consumers finished, client still open: True
4. after_shutdown: client closed
```

Hooks are plain functions that take no arguments, run in the order registered, and can be used as decorators. Use `on_startup` to build resources your handlers need, `on_shutdown` to flush buffers while Redis is still usable, and `after_shutdown` to release anything else.

::: tip The `ping` is a feature
If Redis is down at startup, `start()` raises a `redis.ConnectionError` straight away, so a process manager can restart you, instead of running with silent dead consumers.
:::

## run() versus start()/stop()

| | Blocks? | Handles signals? | Use for |
| --- | --- | --- | --- |
| `broker.run()` | yes | yes (SIGINT, SIGTERM) | a worker process |
| `broker.start()` + `broker.stop()` | no | no | tests, scripts, embedding inside another app |

`run()` is `start()`, then wait, then `stop()`. It returns when a shutdown signal arrives, when `stop()` is called from another thread, or when all consumer threads have died.

```python
broker.run()                          # normal worker
broker.run(shutdown_timeout=30)       # wait at most 30 s for handlers when stopping
broker.run(handle_signals=False)      # you install your own signal handlers
```

`start()` returns immediately because the consumers are daemon threads: if your main thread exits, they die with it. Keep the main thread alive yourself, or use `run()`.

## Signals and graceful shutdown

`run()` installs handlers for `SIGINT` and `SIGTERM` (only when called from the main thread):

- **First signal:** stop asking for new messages, **finish the message currently being handled**, run the shutdown hooks, close the client and return. The process exits with status 0.
- **Second signal:** exits immediately with status 1 (`sys.exit(1)`).

Two details worth knowing:

- A stop can take up to `block_ms` to be noticed, because the consumer is parked in a blocking read. The default is 5 seconds. Lower `block_ms` for faster shutdowns.
- If a consumer has already fetched a batch (`count` entries) when the stop arrives, it finishes the current message and **leaves the rest of the batch unprocessed**. Those entries stay pending and are picked up by another worker once they have been idle for `claim_idle_ms`.

```python [g_leftover.py]
import logging
import time

from rillkit import Broker, Stream

logging.basicConfig(level=logging.WARNING)
broker = Broker("redis://localhost:6379/0")


@broker.subscribe(Stream("tasks", group="g"), consumer="c1", block_ms=200, count=10)
def slow(task: dict):
    time.sleep(0.3)


broker.start()
for i in range(5):
    broker.publish("tasks", {"n": i})
time.sleep(0.5)
c = broker.client
broker.stop()
import redis
r = redis.Redis.from_url("redis://localhost:6379/0")
print("pending after stop:", r.xpending("tasks", "g")["pending"])
```

```text
pending after stop: 3
```

Of five messages, two were handled before the stop took effect and three were left pending. If quick handover matters, use a small `count`.

A full SIGTERM run, with the exact output, is in the [graceful shutdown example](/examples/graceful-shutdown).

## Running several worker processes

A consumer group is designed for this. Start the same program several times, in several processes or containers, and Redis spreads the entries between them:

- Every process uses the same `group`.
- Every process needs a **distinct consumer name**. The default `<group>-<hostname>-<pid>` is unique across machines and processes. Set `consumer=` yourself if you run containers that share a hostname and PID (for instance PID 1 with a fixed hostname).
- Each process gets its own `Broker` and its own Redis connection.
- Pending messages of a crashed worker are picked up by the survivors after `claim_idle_ms`.

See [multiple workers](/examples/multiple-workers) and [Operations](/guide/operations#scaling).

## After stop

`stop()` closes the Redis client, including a client you passed in yourself. Treat a stopped broker as finished, and create a new `Broker` if you need to publish or consume again.

`stop()` is safe to call more than once, and from another thread while `run()` is blocking: the shutdown hooks run and the client closes only once.
