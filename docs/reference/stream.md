# Stream

```python
from rillkit import Stream, Codec, JsonCodec
```

## Stream

```python
@dataclass(frozen=True)
class Stream:
    name: str
    group: Optional[str] = None
    dlq: Optional[str] = None
    maxlen: Optional[int] = None
    codec: Codec = JsonCodec()
```

A stream name plus everything both sides should agree on. It is immutable. Anywhere a `Stream` is accepted, a plain `str` is accepted too and means `Stream(name)`.

| Field | Default | Description |
| --- | --- | --- |
| `name` | required | The Redis key of the stream. |
| `group` | `None` | Consumer group. Needed only by consumers. |
| `dlq` | `None` | Dead letter stream name. When `None` it is `<name>-dlq`. |
| `maxlen` | `None` | Approximate length cap applied when publishing with this `Stream`. A per-call `maxlen` overrides it. |
| `codec` | `JsonCodec()` | Encoder and decoder for the `data` field. Excluded from equality and `repr`. |

### `dlq_name`

```python
Stream.dlq_name -> str
```

Property: `dlq` if set, otherwise `f"{name}-dlq"`.

## Codec

```python
class Codec(Protocol):
    def encode(self, body: Any) -> str: ...
    def decode(self, raw: str) -> Any: ...
```

Any object with these two methods works. `encode` turns a body into the string stored in `data`; `decode` does the reverse. Raise `DecodeError` from `decode` for input it cannot read, so the message is dead-lettered without retries (the built-in codec does this).

## JsonCodec

The default codec.

- `encode(body)`: if `body` has `model_dump_json` (pydantic v2), returns that; otherwise `json.dumps(body, default=str)`.
- `decode(raw)`: `json.loads(raw)`; raises `DecodeError("body is not valid JSON: ...")` on failure.

## Custom codec example

```python [g_codec.py]
import json
import logging
import time

from rillkit import Broker, Stream

logging.basicConfig(level=logging.WARNING)


class CompactJson:
    """Same wire format as the default, but without spaces."""

    def encode(self, body) -> str:
        return json.dumps(body, separators=(",", ":"), sort_keys=True)

    def decode(self, raw: str):
        return json.loads(raw)


EVENTS = Stream("events", group="readers", dlq="events-failed", maxlen=1000, codec=CompactJson())
broker = Broker("redis://localhost:6379/0")


@broker.subscribe(EVENTS, consumer="r1", block_ms=200)
def handle(event: dict):
    print("got", event)


broker.start()
broker.publish(EVENTS, {"b": 2, "a": 1})
time.sleep(0.6)
print(broker.client.xrange("events")[0][1])
print(EVENTS.dlq_name, Stream("events").dlq_name)
broker.stop()
```

```text
got {'a': 1, 'b': 2}
{b'data': b'{"a":1,"b":2}'}
events-failed events-dlq
```

The `dlq="events-failed"` setting is what moves dead letters to a different name; the last line shows the default for comparison.
