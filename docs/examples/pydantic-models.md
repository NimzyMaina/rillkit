# Pydantic models

Requires `pip install "rillkit[pydantic]"`.

```python [pydantic_models.py]
import logging
import time

import redis
from pydantic import BaseModel

from rillkit import Broker, Stream

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

broker = Broker("redis://localhost:6379/0")
ORDERS = Stream("orders-typed", group="billing")


class Order(BaseModel):
    id: int
    total: float
    currency: str = "KES"


@broker.subscribe(ORDERS, consumer="billing-1", block_ms=500)
def handle_order(order: Order):
    print(f"order {order.id}: {order.total:.2f} {order.currency}")


broker.start()
broker.publish(ORDERS, Order(id=1, total=49.5))                    # a model instance
broker.publish(ORDERS, {"id": 2, "total": 12, "currency": "USD"})  # a plain dict works too
broker.publish(ORDERS, {"id": "not-a-number", "total": 5})         # fails validation
time.sleep(1)

# the bad message is in the DLQ, with the reason
for entry_id, fields in broker.client.xrange("orders-typed-dlq"):
    print("DLQ data:", fields[b"data"].decode())
    print("x-error:", fields[b"x-error"].decode().splitlines()[0])
    print("x-deliveries:", fields[b"x-deliveries"].decode())
broker.stop()
```

Output:

```text
INFO consumer started | stream: orders-typed | group: billing | consumer: billing-1 | policy: nack_on_error | max retries: 3
order 1: 49.50 KES
order 2: 12.00 USD
ERROR message 1793094995415-1 cannot be decoded, sending to DLQ: body failed validation: 1 validation error for Order
id
  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='not-a-number', input_type=str]
    For further information visit https://errors.pydantic.dev/2.14/v/int_parsing
WARNING moving message 1793094995415-1 to orders-typed-dlq: body failed validation: 1 validation error for Order
id
  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='not-a-number', input_type=str]
    For further information visit https://errors.pydantic.dev/2.14/v/int_parsing
DLQ data: {"id": "not-a-number", "total": 5}
x-error: body failed validation: 1 validation error for Order
x-deliveries: 1
INFO consumer stopped | stream: orders-typed | consumer: billing-1
```

- Annotating the parameter with `Order` makes rillkit validate the body before calling the handler. `currency` was missing on the first order, so the default `KES` applied.
- `broker.publish` accepts a model instance or a plain dict. Both end up as JSON in the `data` field.
- The third message could not become an `Order`, so it was dead-lettered on its first delivery, without retries, with the validation error in `x-error` (only the first line is printed above). The rillkit log shows the full pydantic message.

See the [Pydantic guide](/guide/pydantic) for the details.
