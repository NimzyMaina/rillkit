import time
from typing import Any, Callable

import redis


def wait_until(cond: Callable[[], Any], timeout: float = 10.0, interval: float = 0.02) -> bool:
    """Poll ``cond`` until it is truthy. Returns the final truthiness instead of raising."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(interval)
    return bool(cond())


def fast(**overrides: Any) -> dict[str, Any]:
    """Subscribe kwargs that make consumers react in milliseconds."""
    opts: dict[str, Any] = {"block_ms": 50, "claim_idle_ms": 150}
    opts.update(overrides)
    return opts


def pending(r: "redis.Redis", stream: str, group: str = "g") -> int:
    return int(r.xpending(stream, group)["pending"])


def read_count(r: "redis.Redis", stream: str, group: str = "g") -> int:
    """How many entries the group has read so far."""
    return int(r.xinfo_groups(stream)[0]["entries-read"] or 0)


def entries(r: "redis.Redis", stream: str) -> list:
    """Entries of a stream as (id, {str: str}) pairs."""
    out = []
    for entry_id, raw in r.xrange(stream):
        out.append((entry_id.decode(), {k.decode(): v.decode() for k, v in raw.items()}))
    return out


def settle(seconds: float) -> None:
    """Sleep to prove something does NOT happen (e.g. no redelivery), never to wait for events."""
    time.sleep(seconds)
