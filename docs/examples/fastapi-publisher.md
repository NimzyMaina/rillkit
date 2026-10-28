# FastAPI publisher

Publish to a stream from a web handler and let a worker do the slow part. The web process only needs a `Broker` for publishing: it never calls `run()` or `start()`.

Requires `pip install fastapi`.

```python [fastapi_app.py]
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from rillkit import Broker, PublishError, Stream

broker = Broker("redis://localhost:6379/0")
SIGNUPS = Stream("signups", maxlen=100_000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    broker.client.close()


app = FastAPI(lifespan=lifespan)


class Signup(BaseModel):
    email: str
    plan: str = "free"


@app.post("/signup", status_code=202)
def signup(body: Signup):
    # A plain `def` endpoint runs in FastAPI's thread pool, so the blocking publish is fine.
    try:
        entry_id = broker.publish(SIGNUPS, body.model_dump())
    except PublishError:
        raise HTTPException(status_code=503, detail="queue unavailable")
    return {"queued": entry_id}
```

Exercising it with FastAPI's test client (`pip install httpx`) against a real Redis:

```python
from fastapi.testclient import TestClient
from fastapi_app import app, broker

with TestClient(app) as client:
    r = client.post("/signup", json={"email": "ada@example.com", "plan": "pro"})
    print(r.status_code, r.json())
    print(broker.client.xrange("signups")[-1])
```

```text
202 {'queued': '1793095048738-0'}
(b'1793095048738-0', {b'data': b'{"email": "ada@example.com", "plan": "pro"}'})
```

- The endpoint is a plain `def`, so FastAPI runs it in a worker thread and the blocking Redis call does not stall the event loop. If you use `async def`, wrap the call: `await run_in_threadpool(broker.publish, SIGNUPS, payload)` (from `starlette.concurrency`).
- `PublishError` is RillKit's single exception for failed publishes. Turning it into a `503` tells the client to retry.
- `status_code=202` says "accepted, not done yet", which is what it means to queue work.
- The stored entry is `{"data": "<json>"}`, so the worker side is just `@broker.subscribe(Stream("signups", group="mailers"))` in another process.
- `maxlen=100_000` keeps the stream bounded.
- Close the client on shutdown (here via the lifespan) so connections are released.
