# Migrating from raw redis-py

Here is the consumer loop most teams write first.

## Before

```python [migrating_before.py]
import json

import redis

r = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
STREAM, GROUP, CONSUMER = "orders", "billing", "billing-1"

try:
    r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
except redis.ResponseError as e:
    if "BUSYGROUP" not in str(e):
        raise

r.xadd(STREAM, {"data": json.dumps({"id": 1, "total": 49.5})})
r.xadd(STREAM, {"data": json.dumps({"id": 2, "total": 12.0})})

seen = 0
while seen < 2:  # in production: while True, plus signal handling
    for _, entries in r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=10, block=1000) or []:
        for entry_id, fields in entries:
            try:
                order = json.loads(fields["data"])
                print(f"billing order {order['id']}: {order['total']}")
                r.xack(STREAM, GROUP, entry_id)
            except Exception as e:
                print("failed:", e)  # and then? no retry, no DLQ, no claiming of stuck entries
            seen += 1
```

```text
billing order 1: 49.5
billing order 2: 12.0
```

It works, but notice what it does not do:

- if the handler raises, the entry stays pending forever, because nothing ever claims it
- crashed workers leave pending entries behind, also forever
- no retry limit, no backoff, no dead letter stream
- no graceful shutdown, no heartbeat, no JSON error handling
- each service re-implements all of this slightly differently

## After

```python [migrating_after.py]
import logging
import time

from rillkit import Broker, Stream

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

broker = Broker("redis://localhost:6379/0")


@broker.subscribe(Stream("orders", group="billing"), consumer="billing-1", block_ms=500)
def handle_order(order: dict):
    print(f"billing order {order['id']}: {order['total']}")


broker.start()
# the producer side is unchanged: this raw redis-py XADD is a valid rillkit message
import json
broker.client.xadd("orders", {"data": json.dumps({"id": 1, "total": 49.5})})
broker.client.xadd("orders", {"data": json.dumps({"id": 2, "total": 12.0})})
time.sleep(1)
broker.stop()
```

```text
INFO consumer started | stream: orders | group: billing | consumer: billing-1 | policy: nack_on_error | max retries: 3
billing order 1: 49.5
billing order 2: 12.0
INFO consumer stopped | stream: orders | consumer: billing-1
```

The same two messages were processed. The group creation, the loop, JSON decoding, acking, claiming stuck entries, retries, dead lettering, signal handling and shutdown now come from the library.

## What carries over

| Raw redis-py | rillkit |
| --- | --- |
| `r.xadd(S, {"data": json.dumps(x)})` | `broker.publish(S, x)`. The wire format is identical, so mixed old and new producers and consumers keep working. |
| `xgroup_create(..., mkstream=True)` and `BUSYGROUP` handling | automatic, with `group_start_id` (`"0"` by default) |
| `xreadgroup(..., ">")` loop | `@broker.subscribe(...)`, one thread per handler |
| `xack` after success | `AckPolicy.NACK_ON_ERROR` (default) |
| a hand-written `XAUTOCLAIM`/`XCLAIM` sweep | `claim_idle_ms`, `max_retries`, `backoff` |
| a `failed` stream | `<stream>-dlq`, with `x-` context fields, and `replay_dlq` |

## Migrating safely

1. Keep the **same stream name** and the **same group name**. rillkit then continues from the group's existing position and also finds your pending entries.
2. Make sure the producers write JSON into a field called `data`. If your entries use other fields, see [Concepts](/guide/concepts#the-wire-format): an entry without `data` goes to the DLQ, so migrate the producer first or reshape the data.
3. Stop the old consumers before starting rillkit ones, or give rillkit a **different consumer name** so the two do not fight. Old pending entries are claimed after `claim_idle_ms`.
4. Check old pending entries first (`XPENDING`). rillkit counts the deliveries Redis has already recorded, so an entry that your old code retried more than `max_retries` times is dead-lettered as soon as rillkit claims it. Raise `max_retries` for the first run if that matters.
5. Delete any retry or claim code you wrote. rillkit handles it.
