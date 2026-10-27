# Message

```python
from rillkit import Message
```

One stream entry as seen by a handler or middleware. rillkit creates it; you normally only read from it.

A handler receives a `Message` when a parameter is annotated `Message`, or is named `msg` or `message` with no annotation. See [Consuming](/guide/consuming#handler-signature-rules).

## Attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `id` | `str` | The entry id, for example `1793094479536-0`. |
| `stream` | `Stream` | The stream (with its group and codec) this message came from. |
| `raw` | `dict[str, str]` | All fields of the entry as text, including `data`. |
| `deliveries` | `int` | How many times Redis has delivered this entry to the group, counting the current one. `1` on the first delivery. |
| `consumer` | `str` | Name of the consumer that holds the message. |
| `acked` | `bool` | `True` once the message has been acknowledged (or dead-lettered). |
| `nacked` | `bool` | `True` after `nack()` until it is acked. |
| `rejected` | `bool` | `True` after `reject()`. |
| `reject_reason` | `Optional[str]` | The reason passed to `reject()`. |
| `error` | `Optional[BaseException]` | The exception the handler raised, set only when it failed with an ordinary exception. |
| `body` | `Any` | Property: the decoded payload (a `dict` for a JSON object). Decoded on first access and cached. Raises `DecodeError` if there is no `data` field or it cannot be decoded. |

You can also attach your own attributes, for example per-message state in middleware (`msg.started = ...`).

## Methods

### `ack()`

Acknowledges the message with `XACK` so it leaves the pending list and is never redelivered. Calling it twice is harmless. Sets `acked = True` and `nacked = False`.

### `nack()`

Marks the message failed so it stays pending and is retried after `claim_idle_ms`, or dead-lettered if retries are used up. Does nothing if the message was already acked. Sets `nacked = True`.

### `reject(reason=None)`

Skips the remaining retries. When the handler finishes, rillkit copies the entry to the DLQ with `reason` as `x-error` and acks it. Works under every `AckPolicy`. Sets `rejected = True` and `nacked = False`. A later exception or `nack()` in the same handler does not undo it.

### `repr`

`Message(id='1793094479536-0', stream='orders', deliveries=1)`
