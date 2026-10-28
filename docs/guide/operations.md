# Operations

## Heartbeat and active_workers

Every consumer writes a heartbeat key, `rillkit:workers:<stream>:<group>:<consumer>`, with a time-to-live of `heartbeat_ttl` seconds (default 60). It is refreshed at the top of every loop and after every message, and deleted on a clean shutdown. A worker that crashes simply stops refreshing it and drops off after the TTL.

```python
broker.active_workers("orders", group="billing")   # ['billing-web1-4242', 'billing-web2-977']
broker.active_workers(Stream("orders", group="billing"))
```

`active_workers` returns the sorted consumer names whose heartbeat is alive. `XINFO CONSUMERS` only lists consumers that have already received a message, so it misses idle workers. The heartbeat does not.

```python [g_ops.py]
import time
import logging
from rillkit import Broker, Stream

logging.basicConfig(level=logging.WARNING)
broker = Broker("redis://localhost:6379/0")
S = Stream("tasks", group="workers")


@broker.subscribe(S, consumer="w1", block_ms=200)
def a(task: dict):
    pass


broker.start()
broker.publish(S, {"n": 1})
time.sleep(0.5)
print(broker.active_workers(S))
print(broker.active_workers("tasks", group="workers"))
print(sorted(k.decode() for k in broker.client.scan_iter("rillkit:workers:*:*")) )
print(broker.client.ttl("rillkit:workers:tasks:workers:w1"))
broker.stop()
print("after stop:", Broker("redis://localhost:6379/0").active_workers(S))
```

```text
['w1']
['w1']
['rillkit:workers:tasks:workers:w1']
60
after stop: []
```

::: warning Long handlers and the heartbeat
The heartbeat is refreshed between messages, not during a handler. A handler that runs longer than `heartbeat_ttl` makes a busy, healthy worker look gone. Set `heartbeat_ttl` above your longest handler, or pass `heartbeat=False` to turn the feature off.
:::

## Scaling

- One subscription is one thread, processing one message at a time.
- Scale by running more worker processes in the same group (see [Lifecycle](/guide/lifecycle#running-several-worker-processes)), or by adding more `@broker.subscribe` handlers on different streams.
- Redis spreads new entries over the consumers in the group, so throughput rises with the number of workers. Ordering across workers is not guaranteed.
- Keep an eye on `count`: a larger batch means a worker holds more entries pending at a time, and on shutdown the unprocessed part of a batch waits for `claim_idle_ms`.

## Claim tuning

| Setting | Lower it when | Raise it when |
| --- | --- | --- |
| `claim_idle_ms` | you want failed or abandoned messages back sooner | handlers are slow: it must exceed the longest handler |
| `backoff` (`> 1`) | retries should space out when a dependency is down | retries should stay quick |
| `block_ms` | you want fast retries and fast shutdown | you want fewer round trips on a quiet stream |
| `count` | handlers are slow and you want fair sharing | handlers are fast and you want fewer round trips |

Recovery time for the work of a crashed worker is roughly `claim_idle_ms` plus up to `block_ms`.

## Trimming

Streams keep every entry until you remove it. Choose one:

- `Stream("orders", maxlen=100_000)` or `publish(..., maxlen=...)` trims on write (approximately; pass `approximate=False` to `publish` for an exact cap).
- A scheduled job running `XTRIM orders MAXLEN ~ 100000`.

RillKit never trims the dead letter stream. Cap it yourself, for example with `redis-cli XTRIM orders-dlq MAXLEN ~ 10000`, and watch its length. `Idempotent` markers expire on their own after `ttl`.

## Monitoring with redis-cli

Everything RillKit does is visible in plain Redis. These are real outputs from a worker (`w1`) that handled four messages, one of which failed and is waiting for its retry. `redis-cli` prints one value per line when piped, as below:

```bash
redis-cli XLEN tasks                       # entries in the stream
redis-cli XINFO GROUPS tasks               # per group: consumers, pending, lag
redis-cli XINFO CONSUMERS tasks workers    # per consumer: pending, idle
redis-cli XPENDING tasks workers           # summary of the pending list
redis-cli XPENDING tasks workers - + 10    # detail: id, consumer, idle ms, deliveries
redis-cli XRANGE tasks-dlq - +             # dead letters
redis-cli KEYS 'rillkit:workers:*'         # live heartbeats (avoid KEYS on big databases)
```

```text
$ redis-cli XLEN tasks
4

$ redis-cli XINFO GROUPS tasks
name
workers
consumers
1
pending
1
last-delivered-id
1793095029760-0
entries-read
4
lag
0

$ redis-cli XINFO CONSUMERS tasks workers
name
w1
pending
1
idle
151
inactive
1065

$ redis-cli XPENDING tasks workers
1
1793095029759-0
1793095029759-0
w1
1

$ redis-cli XPENDING tasks workers - + 10
1793095029759-0
w1
1094
1

$ redis-cli KEYS rillkit:workers:*
rillkit:workers:tasks:workers:w1
```

What to watch:

| Signal | Meaning |
| --- | --- |
| `lag` in `XINFO GROUPS` keeps growing | consumers are not keeping up or are down |
| `pending` stays high, `idle` is large | handlers are stuck or messages keep failing |
| `XPENDING` deliveries count rising | a message is being retried |
| `XLEN <stream>-dlq` above zero | something gave up, go and look |
| `active_workers` smaller than expected | a worker died or its heartbeat expired |

In the output above, `XPENDING` shows one entry delivered once and owned by `w1`. That is the failed message waiting out `claim_idle_ms`.
