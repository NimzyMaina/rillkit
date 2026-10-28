"""The default blocking read (5 s) must not collide with the Redis client's socket timeout.

redis-py 8 changed the default socket_timeout from "none" to 5 s, which equals rillkit's default
block_ms, so an idle consumer's read timed out right as the server would have replied.
"""

import logging
import time

import redis

from helpers import keep_server_awake, wait_until
from rillkit import Broker, Settings, Stream


def _run_idle_then_publish(
    broker: Broker, stream: Stream, caplog, idle_seconds: float, url: str
) -> list:
    got: list = []

    @broker.subscribe(stream)  # library defaults: block_ms=5000, heartbeat on
    def handle(body: dict):
        got.append(body)

    with keep_server_awake(url), caplog.at_level(logging.ERROR, logger="rillkit"):
        broker.start()
        time.sleep(idle_seconds)
        broker.publish(stream, {"n": 1})
        assert wait_until(lambda: got, timeout=8)
        broker.stop()
    errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors == []
    return got


def test_default_block_with_short_client_timeout(redis_url, name, caplog):
    """A caller-supplied client with a 2 s socket timeout and the default 5 s block."""
    client = redis.Redis.from_url(redis_url, socket_timeout=2)
    broker = Broker(client=client)
    stream = Stream(name, group="g")
    _run_idle_then_publish(broker, stream, caplog, idle_seconds=4, url=redis_url)
    assert broker.subscribers[0]._block_ms < 2000  # clamped below the socket timeout


def test_default_settings_survive_an_idle_period(redis_url, name, caplog):
    """The client rillkit builds itself works with the defaults across more than one idle pass."""
    broker = Broker(settings=Settings(url=redis_url))
    stream = Stream(name, group="g")
    _run_idle_then_publish(broker, stream, caplog, idle_seconds=6, url=redis_url)


def test_settings_socket_timeout_comes_from_env(monkeypatch):
    monkeypatch.setenv("REDIS_SOCKET_TIMEOUT", "30")
    assert Settings.from_env().socket_timeout == 30.0
    monkeypatch.setenv("REDIS_SOCKET_TIMEOUT", "none")
    assert Settings.from_env().socket_timeout is None
