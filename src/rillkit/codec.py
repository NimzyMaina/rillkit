import json
from typing import Any, Protocol

from .exceptions import DecodeError


class Codec(Protocol):
    def encode(self, body: Any) -> str: ...

    def decode(self, raw: str) -> Any: ...


class JsonCodec:
    """JSON in the ``data`` field of the stream entry.

    Pydantic models are dumped with ``model_dump_json``.
    """

    def encode(self, body: Any) -> str:
        if hasattr(body, "model_dump_json"):
            return body.model_dump_json()
        return json.dumps(body, default=str)

    def decode(self, raw: str) -> Any:
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as e:
            raise DecodeError(f"body is not valid JSON: {e}") from e
