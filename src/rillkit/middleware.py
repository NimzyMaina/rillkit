from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional

from .exceptions import AckMessage
from .message import Message

if TYPE_CHECKING:
    from .broker import Broker
    from .stream import Stream


@dataclass
class PublishCommand:
    """What ``publish_scope`` receives. Mutate it to change what gets published."""

    stream: "Stream"
    body: Any
    maxlen: Optional[int] = None
    approximate: bool = True


class BaseMiddleware:
    """Subclass and override any hook. Instances are shared by all messages, so keep per-message
    state on the ``Message``, not on ``self``. ``self.broker`` is set when the middleware is added.

    Order: ``on_receive`` -> ``consume_scope`` (wraps decode + handler) -> ``after_processed``.
    The first middleware in the list is the outermost.
    """

    broker: "Broker"

    def on_receive(self, msg: Message) -> None:
        """Called first for every delivered message, before decoding."""

    def consume_scope(self, call_next: Callable[[Message], Any], msg: Message) -> Any:
        """Wrap the handler call. Raise ``AckMessage``/``NackMessage`` to short-circuit."""
        return call_next(msg)

    def publish_scope(self, call_next: Callable[[PublishCommand], str], cmd: PublishCommand) -> str:
        """Wrap every publish, including handler return values."""
        return call_next(cmd)

    def after_processed(self, msg: Message, exc: Optional[BaseException]) -> None:
        """Always called last. ``exc`` is the handler error, if any."""


class Idempotent(BaseMiddleware):
    """Skip messages whose key was already processed successfully.

    Redis delivers at least once, so a crash after the handler finished but before the ack means a
    redelivery. The key is stored with ``ttl`` seconds once the handler returns without raising.

        broker = Broker(middlewares=[Idempotent(key=lambda m: m.body["request_id"])])
    """

    def __init__(
        self,
        key: Callable[[Message], str],
        ttl: int = 7 * 24 * 3600,
        prefix: str = "rillkit:done:",
    ):
        self.key = key
        self.ttl = ttl
        self.prefix = prefix

    def _redis_key(self, msg: Message) -> str:
        return f"{self.prefix}{msg.stream.name}:{self.key(msg)}"

    def consume_scope(self, call_next: Callable[[Message], Any], msg: Message) -> Any:
        redis_key = self._redis_key(msg)
        if self.broker.client.exists(redis_key):
            raise AckMessage()
        result = call_next(msg)
        self.broker.client.set(redis_key, msg.id, ex=self.ttl)
        return result
