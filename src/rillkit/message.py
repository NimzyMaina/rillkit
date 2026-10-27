from typing import TYPE_CHECKING, Any, Optional

from .exceptions import DecodeError
from .stream import Stream

if TYPE_CHECKING:
    import redis

_MISSING = object()


class Message:
    """One stream entry as seen by a handler or middleware.

    ``body`` is the decoded payload (a plain dict for JSON objects). ``deliveries`` is how many
    times Redis has delivered this entry to a consumer in the group, counting the current one.
    """

    def __init__(
        self,
        id: str,
        stream: Stream,
        raw: dict[str, str],
        deliveries: int,
        consumer: str,
        client: "redis.Redis",
    ) -> None:
        self.id = id
        self.stream = stream
        self.raw = raw
        self.deliveries = deliveries
        self.consumer = consumer
        self.acked = False
        self.nacked = False
        self.rejected = False
        self.reject_reason: Optional[str] = None
        self._client = client
        self._body: Any = _MISSING
        self.error: Optional[BaseException] = None

    @property
    def body(self) -> Any:
        if self._body is _MISSING:
            if "data" not in self.raw:
                raise DecodeError("entry has no 'data' field")
            self._body = self.stream.codec.decode(self.raw["data"])
        return self._body

    def ack(self) -> None:
        """Acknowledge the message. It is removed from the pending list and never redelivered."""
        if self.acked:
            return
        assert self.stream.group is not None  # only consumed streams have messages
        self._client.xack(self.stream.name, self.stream.group, self.id)
        self.acked = True
        self.nacked = False

    def nack(self) -> None:
        """Leave the message pending so it is retried (or sent to the DLQ once retries run out)."""
        if not self.acked:
            self.nacked = True

    def reject(self, reason: Optional[str] = None) -> None:
        """Skip the remaining retries: the message goes to the DLQ as soon as the handler finishes.

        Use it for messages that can never succeed (bad input, unknown customer). ``reason`` is
        stored as ``x-error`` in the DLQ entry. Works under every ``AckPolicy``.
        """
        self.rejected = True
        self.reject_reason = reason
        self.nacked = False

    def __repr__(self) -> str:
        return f"Message(id={self.id!r}, stream={self.stream.name!r}, deliveries={self.deliveries})"
