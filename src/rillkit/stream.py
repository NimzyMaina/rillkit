from dataclasses import dataclass, field
from typing import Optional, Union

from .codec import Codec, JsonCodec


@dataclass(frozen=True)
class Stream:
    """A stream name plus everything that should be agreed on by both sides.

    ``group`` is only needed by consumers. ``dlq`` defaults to ``<name>-dlq``.
    """

    name: str
    group: Optional[str] = None
    dlq: Optional[str] = None
    maxlen: Optional[int] = None
    codec: Codec = field(default_factory=JsonCodec, compare=False, repr=False)

    @property
    def dlq_name(self) -> str:
        return self.dlq or f"{self.name}-dlq"


StreamLike = Union[str, Stream]


def as_stream(stream: StreamLike) -> Stream:
    return stream if isinstance(stream, Stream) else Stream(stream)
