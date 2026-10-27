# AckPolicy

```python
from rillkit import AckPolicy
```

`AckPolicy` is a `str` enum. Pass it as `ack_policy=` to `broker.subscribe`. The string values are also accepted: `ack_policy="manual"`.

| Member | Value | Behaviour |
| --- | --- | --- |
| `NACK_ON_ERROR` | `"nack_on_error"` | Ack when the handler returns, nack when it raises. This is the default. |
| `ACK_ALWAYS` | `"ack_always"` | Ack when the handler returns or raises. Failures are logged and dropped, never retried. |
| `ACK_FIRST` | `"ack_first"` | Ack before the handler runs. At most once: a crash loses the message. |
| `MANUAL` | `"manual"` | rillkit does not ack on success. The handler must call `msg.ack()` or `msg.nack()`. An exception from a `MANUAL` handler is still nacked. |

In every policy, `AckMessage` acks the message and `NackMessage` nacks it, a decode error goes straight to the DLQ, and a message that has been nacked more than `max_retries` times is dead-lettered.

See [Ack policies](/guide/ack-policies) for a comparison with real output.
