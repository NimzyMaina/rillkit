# Concepts

If you already know Redis Streams, skim the headings and jump to [the wire format](#the-wire-format). If not, this page is the short version of the [Redis Streams documentation](https://redis.io/docs/latest/develop/data-types/streams/).

## Streams

A **stream** is an append-only log stored under one Redis key. Every entry gets an id such as `1793094479536-0` (milliseconds since the epoch, then a sequence number) and a set of field/value pairs. Entries stay in the stream after they are read. Producers add with `XADD`; nothing is removed unless you trim the stream.

## Consumer groups

A **consumer group** lets several workers share one stream. Redis remembers, per group, which entries have been handed out. When a worker asks for new entries with `XREADGROUP`, it gets entries nobody else in the group has received. Add workers to scale out; give each group its own name if two services each need every message.

| You want | Use |
| --- | --- |
| Many workers sharing the work | the same `group` name |
| Two services that each see every message | different `group` names on the same stream |

Each worker in a group is a **consumer** with a name. RillKit names it `<group>-<hostname>-<pid>` unless you pass `consumer=`.

## The pending list and ack

When Redis hands an entry to a consumer, it records it in the group's **pending entries list** (PEL). The entry stays there, assigned to that consumer, until the consumer sends `XACK`. This is how Redis knows about work that is in flight.

If a worker crashes mid-message, the entry just stays in the PEL. Nothing is lost, but nothing happens to it either, unless something else notices and takes it over with `XCLAIM`. Redis does not do that on its own.

## How RillKit retries

RillKit uses the pending list as its retry queue. There is no separate retry stream.

1. A handler raises. RillKit does not `XACK`, so the entry stays pending.
2. Every loop, each consumer asks Redis for pending entries that have been idle for at least `claim_idle_ms` (`XPENDING ... IDLE`).
3. Entries that are due are taken over with `XCLAIM`, which bumps the delivery counter, and handed to the handler again.
4. When an entry has been delivered more than `max_retries` times, RillKit copies it to the dead letter stream (`<name>-dlq`) and acknowledges the original.

The same mechanism recovers messages from crashed workers: a dead worker's entries go idle, then any surviving consumer in the group claims them. Because of this, **delivery is at least once**. Handlers should be safe to run twice for the same message (see [`Idempotent`](/guide/middleware#idempotent)).

::: details The whole life of a message
```text
XADD  ->  XREADGROUP  ->  handler  ->  XACK                    (happy path)
                              |
                              +-> raises -> stays pending
                                              |
                              idle >= claim_idle_ms
                                              |
                                           XCLAIM -> handler again
                                              |
                              deliveries > max_retries
                                              |
                                  XADD <name>-dlq + XACK
```
:::

## The wire format

RillKit stores each message as **one stream field called `data`, holding a JSON string**:

```text
XADD orders * data '{"id": 1, "total": 49.5}'
```

That is the entire protocol. It means anything that can talk to Redis can interoperate with RillKit, in either direction.

```python [g_interop.py]
import json
import time

import redis

from rillkit import Broker, Stream

URL = "redis://localhost:6379/0"
r = redis.Redis.from_url(URL, decode_responses=True)
broker = Broker(URL)


@broker.subscribe(Stream("orders", group="billing"), consumer="billing-1", block_ms=300)
def handle(order: dict):
    print("rillkit consumer got:", order)


broker.start()

# 1. a plain redis-py producer
r.xadd("orders", {"data": json.dumps({"id": 1, "source": "redis-py"})})

# 2. rillkit publishes, a plain redis-py consumer reads
entry_id = broker.publish("orders", {"id": 2, "source": "rillkit"})
time.sleep(0.8)
for _id, fields in r.xrange("orders"):
    print(_id, fields)
broker.stop()
```

```text
rillkit consumer got: {'id': 1, 'source': 'redis-py'}
rillkit consumer got: {'id': 2, 'source': 'rillkit'}
1793095012841-0 {'data': '{"id": 1, "source": "redis-py"}'}
1793095012844-0 {'data': '{"id": 2, "source": "rillkit"}'}
```

The first order was added by plain `redis-py`; the second by RillKit and read back by plain `redis-py`. Both reached the RillKit consumer.

Rules to keep in mind:

- A producer must put JSON in the `data` field. Other fields are ignored by the handler, but you can read them from `msg.raw`.
- An entry with no `data` field, or with `data` that is not valid JSON, cannot be decoded. RillKit sends it straight to the DLQ without retrying (see [Retries and the DLQ](/guide/retries-and-dlq#decode-errors-skip-retries)).
- The stream is the contract between services. `Stream(...)` objects exist so both sides can share the name, DLQ name, length cap and codec in one place.
- If you want a different encoding, pass a `codec` to `Stream`. See the [Stream reference](/reference/stream).
