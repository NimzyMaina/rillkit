# Exceptions

```python
from rillkit import RillkitError, PublishError, DecodeError, AckMessage, NackMessage, RejectMessage
```

All inherit from `RillkitError`, which inherits from `Exception`.

| Exception | Raised by | Meaning |
| --- | --- | --- |
| `RillkitError` | | Base class for every RillKit error. |
| `PublishError` | `broker.publish` and publishers | The message could not be written to the stream (Redis error, or a body the codec could not encode). The underlying error is available as `__cause__`. |
| `DecodeError` | codecs, `Message.body`, pydantic validation | The body could not be decoded or validated. Never retried: the message goes straight to the DLQ. |
| `AckMessage` | you, in a handler or middleware | Stops processing and acknowledges the message. |
| `RejectMessage` | you, in a handler or middleware | Stops processing and sends the message to the DLQ immediately, skipping retries. The text becomes `x-error`. |
| `NackMessage` | you, in a handler or middleware | Stops processing and nacks the message so it is retried (or dead-lettered once retries run out). |

`AckMessage`, `NackMessage` and `RejectMessage` are control flow, not errors. Pass text (`NackMessage("rate limited")`) so the DLQ `x-error` field says why; with no text it falls back to the exception class name.

Any other exception from a handler counts as a failure and is handled according to the [ack policy](/reference/ack-policy).
