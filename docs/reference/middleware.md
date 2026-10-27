# Middleware

```python
from rillkit import BaseMiddleware, Idempotent, PublishCommand
```

## BaseMiddleware

Subclass it and override any hook. The default implementations do nothing and pass through. One instance is shared by all messages, so keep per-message state on the `Message`. `self.broker` is set when the middleware is added to a broker or a subscriber.

| Hook | Signature | When |
| --- | --- | --- |
| `on_receive` | `(self, msg: Message) -> None` | First, for every delivered message, before decoding. |
| `consume_scope` | `(self, call_next: Callable[[Message], Any], msg: Message) -> Any` | Wraps decoding plus the handler. Return `call_next(msg)`. Raise `AckMessage` or `NackMessage` to short-circuit. |
| `publish_scope` | `(self, call_next: Callable[[PublishCommand], str], cmd: PublishCommand) -> str` | Wraps every publish, including handler return values. Only broker-wide middleware takes part. |
| `after_processed` | `(self, msg: Message, exc: Optional[BaseException]) -> None` | Always called last. `exc` is the handler error, if any. Errors raised here are logged and ignored. |

The first middleware in a list is the outermost. Broker-wide middleware wraps a subscriber's own. See [Middleware](/guide/middleware) for the full ordering.

## PublishCommand

```python
@dataclass
class PublishCommand:
    stream: Stream
    body: Any
    maxlen: Optional[int] = None
    approximate: bool = True
```

What `publish_scope` receives. Mutate its fields to change what gets published.

## Idempotent

```python
Idempotent(
    key: Callable[[Message], str],
    ttl: int = 7 * 24 * 3600,
    prefix: str = "rillkit:done:",
)
```

Skips messages whose key was already processed successfully.

| Parameter | Default | Description |
| --- | --- | --- |
| `key` | required | Returns the idempotency key for a message, for example `lambda m: m.body["request_id"]`. |
| `ttl` | `604800` | Seconds the done-marker is kept. |
| `prefix` | `"rillkit:done:"` | Redis key prefix. The full key is `<prefix><stream name>:<key>`. |

Behaviour: if the key exists, it raises `AckMessage` (the duplicate is acknowledged and the handler is skipped). Otherwise it calls the handler and, if it returned without raising, stores the key with `SET ... EX ttl` and the message id as value.
