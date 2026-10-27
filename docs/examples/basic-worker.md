# Basic worker

The smallest useful consumer. The handler takes the decoded body and, because it also has a `Message` parameter, the delivery details.

```python [basic_worker.py]
import logging
import time

from rillkit import Broker, Message, Stream

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

broker = Broker("redis://localhost:6379/0")
ORDERS = Stream("orders", group="billing")


@broker.subscribe(ORDERS, consumer="billing-1", block_ms=500)
def handle_order(order: dict, msg: Message):
    print(f"[{msg.id}] delivery {msg.deliveries}: order {order['id']} total={order['total']}")


broker.start()
for i in range(3):
    broker.publish(ORDERS, {"id": i, "total": 10 * (i + 1)})
time.sleep(1)
broker.stop()
```

Output:

```text
INFO consumer started | stream: orders | group: billing | consumer: billing-1 | policy: nack_on_error | max retries: 3
[1793094991699-0] delivery 1: order 0 total=10
[1793094991700-0] delivery 1: order 1 total=20
[1793094991700-1] delivery 1: order 2 total=30
INFO consumer stopped | stream: orders | consumer: billing-1
```

Things to notice:

- `order: dict` is the JSON body. `msg: Message` is the stream entry: its `id`, how many times it was `deliveries`, which `consumer` has it and more (see the [Message reference](/reference/message)).
- `consumer="billing-1"` gives the worker a fixed name. The default is `<group>-<hostname>-<pid>`.
- The script does not call `run()`. `start()` returns immediately, `stop()` finishes in-flight work and closes the connection. For a long-running service use `broker.run()`.
- Each message's first delivery shows `delivery 1`. A retry would show a higher number.
