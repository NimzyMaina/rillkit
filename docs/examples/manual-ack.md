# Manual ack

With `AckPolicy.MANUAL` RillKit never acknowledges for you on success. Your handler decides: `msg.ack()` when the work is truly done or hopeless, `msg.nack()` to ask for a retry, `msg.reject(reason)` to skip retries and dead-letter it (see [Reject vs nack](/examples/reject-vs-nack)).

```python [manual_ack.py]
import logging
import time

from rillkit import AckPolicy, Broker, Message, Stream

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

broker = Broker("redis://localhost:6379/0")
UPLOADS = Stream("uploads", group="thumbnailers")


@broker.subscribe(UPLOADS, consumer="thumb-1", ack_policy=AckPolicy.MANUAL,
                  max_retries=2, claim_idle_ms=300, block_ms=200)
def make_thumbnail(upload: dict, msg: Message):
    if upload["kind"] == "unsupported":
        print(f"{upload['file']}: unsupported, acking so it is not retried")
        msg.ack()
        return
    if upload["kind"] == "slow-disk" and msg.deliveries < 2:
        print(f"{upload['file']}: disk busy, asking for a retry")
        msg.nack()
        return
    print(f"{upload['file']}: thumbnail written (delivery {msg.deliveries})")
    msg.ack()


broker.start()
for file, kind in [("a.png", "image"), ("b.xyz", "unsupported"), ("c.png", "slow-disk")]:
    broker.publish(UPLOADS, {"file": file, "kind": kind})
time.sleep(2)
print("pending:", broker.client.xpending(UPLOADS.name, UPLOADS.group)["pending"])
broker.stop()
```

Output:

```text
INFO consumer started | stream: uploads | group: thumbnailers | consumer: thumb-1 | policy: manual | max retries: 2
a.png: thumbnail written (delivery 1)
b.xyz: unsupported, acking so it is not retried
c.png: disk busy, asking for a retry
c.png: thumbnail written (delivery 2)
pending: 0
INFO consumer stopped | stream: uploads | consumer: thumb-1
```

- `a.png` was processed and acked.
- `b.xyz` is a poison message: retrying cannot help, so the handler acked it deliberately to get rid of it.
- `c.png` nacked on the first delivery. After `claim_idle_ms` it came back as delivery 2 and succeeded.
- `pending: 0` at the end shows every message was settled.

Every path must end in `ack()` or `nack()`. A `MANUAL` handler that returns without either leaves the message pending until it is claimed again. See [Ack policies](/guide/ack-policies).
