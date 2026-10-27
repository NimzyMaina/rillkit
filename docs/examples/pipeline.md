# Two-stage pipeline

A common shape: one stage extracts something from raw input, the next one engineers features from it. Each stage is a consumer group on its own stream, and `@broker.publisher` connects them by publishing a handler's return value.

```text
documents --[extract]--> features --[engineer]--> (your model, a database, ...)
```

```python [pipeline.py]
import logging
import time

from rillkit import Broker, Stream

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

broker = Broker("redis://localhost:6379/0")

DOCUMENTS = Stream("documents", group="extractors")
FEATURES = Stream("features", group="modelers", maxlen=10_000)


@broker.subscribe(DOCUMENTS, consumer="extractor-1", block_ms=500)
@broker.publisher(FEATURES)
def extract(doc: dict) -> dict:
    """Stage 1: pull raw text out of a document. The return value is published to `features`."""
    words = doc["text"].split()
    return {"doc_id": doc["id"], "words": words}


@broker.subscribe(FEATURES, consumer="modeler-1", block_ms=500)
def engineer(features: dict):
    """Stage 2: turn the extracted words into model features."""
    words = features["words"]
    print(f"doc {features['doc_id']}: n_words={len(words)} avg_len={sum(map(len, words)) / len(words):.2f}")


broker.start()
broker.publish(DOCUMENTS, {"id": "a1", "text": "redis streams are a log"})
broker.publish(DOCUMENTS, {"id": "a2", "text": "consumer groups share the work"})
time.sleep(1.5)
broker.stop()
```

Output:

```text
INFO consumer started | stream: documents | group: extractors | consumer: extractor-1 | policy: nack_on_error | max retries: 3
INFO consumer started | stream: features | group: modelers | consumer: modeler-1 | policy: nack_on_error | max retries: 3
doc a1: n_words=5 avg_len=3.80
doc a2: n_words=5 avg_len=5.20
INFO consumer stopped | stream: features | consumer: modeler-1
INFO consumer stopped | stream: documents | consumer: extractor-1
```

How it fits together:

- `extract` is subscribed to `documents` and decorated with `@broker.publisher(FEATURES)`. Whatever it returns goes to the `features` stream. Return `None` to publish nothing for a document.
- `engineer` is an ordinary consumer of `features`. It has no idea where its input came from, only the stream contract.
- Each stage retries and dead-letters on its own. If `engineer` fails, `features-dlq` fills up while `documents` keeps flowing.
- `maxlen=10_000` on `FEATURES` caps the intermediate stream so it cannot grow forever.
- Both stages can live in one process, as here, or in separate processes. Since the stream is the only link, you can split them without changing any code.
- Stack more publishers to fan out: add `@broker.publisher("audit")` below the first and both streams get the result.
