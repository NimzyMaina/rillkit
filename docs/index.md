---
layout: page
pageClass: rill-landing
title: RillKit
titleTemplate: Redis Streams for Python
description: Publish and consume Redis Streams in Python with consumer groups, retries, a dead-letter queue, ack policies and middleware.
---

<RillHero />

<RillConnect>
<template #publish>

```python [publish.py]
from rillkit import Broker

broker = Broker.from_env()

broker.publish("orders", {"id": 1, "total": 42.5})
```

</template>
<template #consume>

```python [worker.py]
from rillkit import AckPolicy, Broker, Message, Stream

broker = Broker.from_env()

@broker.subscribe(
    Stream("orders", group="workers"),
    ack_policy=AckPolicy.NACK_ON_ERROR,
    max_retries=3,
)
def handle(order: dict, msg: Message):
    if order["total"] <= 0:
        msg.reject("bad total")  # straight to the DLQ
        return
    if not charge(order):
        msg.nack()  # try again after a backoff

broker.run()
```

</template>
</RillConnect>

<RillFlow />

<RillDivider :seed="5" :tone="1" />

<RillRedis />

<RillBefore>
<template #before>

```python [consumer_raw.py]
import json

import redis

r = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
try:
    r.xgroup_create("orders", "workers", id="0", mkstream=True)
except redis.ResponseError as e:
    if "BUSYGROUP" not in str(e):
        raise

while True:
    for _, entries in r.xreadgroup("workers", "web1", {"orders": ">"}, count=10, block=5000) or []:
        for entry_id, fields in entries:
            try:
                charge(json.loads(fields["data"]))
                r.xack("orders", "workers", entry_id)
            except Exception as e:
                print("failed:", e)  # and then?
```

</template>
<template #after>

```python [worker.py]
from rillkit import Broker, Stream

broker = Broker.from_env()

@broker.subscribe(Stream("orders", group="workers"))
def handle(order: dict):
    charge(order)

broker.run()
```

</template>
</RillBefore>

<RillSpec />

<RillDivider :seed="9" :tone="3" />

<RillStart />
