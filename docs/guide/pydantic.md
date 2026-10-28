# Pydantic models

Pydantic is **optional**. Without it, handlers receive plain Python values and a JSON object arrives as a `dict`. Install the extra if you want validated, typed handlers:

```bash
pip install "rillkit[pydantic]"
```

## Typed handlers

Annotate the handler parameter with a model class. RillKit calls `Model.model_validate(body)` and passes the instance:

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

## Validation failures go to the DLQ

The third message had `"id": "not-a-number"`. Retrying could never fix that, so RillKit raised a decode error, skipped the retry cycle and moved the entry to `orders-typed-dlq` on the first delivery (`x-deliveries` is `1`). The `x-error` field holds pydantic's explanation. See [Retries and the DLQ](/guide/retries-and-dlq#decode-errors-skip-retries).

## Publishing models

`broker.publish(stream, model)` accepts a model instance and stores `model.model_dump_json()` in `data`. A handler decorated with `@broker.publisher(...)` can return a model too.

```python
@broker.subscribe(RAW)
@broker.publisher(CLEAN)
def clean(order: RawOrder) -> CleanOrder:
    return CleanOrder(id=order.id, total=order.total)
```

On the wire it is still plain JSON, so non-pydantic consumers can read it.

## Details

- Only a plain model class as the annotation triggers validation. `Optional[Order]` or `list[Order]` are passed through as the raw decoded body.
- Any class with a `model_validate` method is treated as a model (pydantic v2 style).
- The handler can take both a model and a `Message`: `def handle(order: Order, msg: Message)`.
- If you annotate with `dict`, there is no validation. That is the default behaviour.
