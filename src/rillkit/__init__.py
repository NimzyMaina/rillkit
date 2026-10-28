"""rillkit: simple publish and consume for Redis Streams."""

from .ack import AckPolicy
from .broker import Broker, Publisher
from .codec import Codec, JsonCodec
from .exceptions import (
    AckMessage,
    DecodeError,
    NackMessage,
    PublishError,
    RejectMessage,
    RillkitError,
)
from .message import Message
from .middleware import BaseMiddleware, Idempotent, PublishCommand
from .settings import Settings
from .stream import Stream

__version__ = "0.1.1"

__all__ = [
    "AckMessage", "AckPolicy", "BaseMiddleware", "Broker", "Codec", "DecodeError", "Idempotent",
    "JsonCodec", "Message", "NackMessage", "PublishCommand", "PublishError", "Publisher",
    "RejectMessage", "RillkitError", "Settings", "Stream",
]
