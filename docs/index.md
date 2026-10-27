---
layout: page
pageClass: rill-landing
title: rillkit
titleTemplate: Redis Streams that flow
description: Publish and consume Redis Streams in Python with consumer groups, retries, a dead-letter queue, ack policies and middleware.
---

<RillHero />

<RillCode>
<template #publish>

```python
from rillkit import Broker

broker = Broker.from_env()

broker.publish("orders", {"id": 1, "total": 42.5})
```

</template>
<template #consume>

```python
from rillkit import Broker, Stream

broker = Broker.from_env()

@broker.subscribe(Stream("orders", group="workers"))
def handle(order: dict):
    print("charging", order["id"])

broker.run()
```

</template>
</RillCode>

<RillFeatures />

<RillFlow />

<RillCta />
