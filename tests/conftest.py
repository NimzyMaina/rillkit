import os
import uuid
from collections.abc import Iterator
from typing import Callable

import pytest
import redis

from rillkit import Broker

TEST_DB = 15


@pytest.fixture(scope="session")
def redis_url() -> str:
    return os.environ.get("REDIS_URL", f"redis://localhost:6390/{TEST_DB}")


@pytest.fixture
def r(redis_url: str) -> Iterator["redis.Redis"]:
    """A raw client for arranging and inspecting state. Only db 15 is ever flushed."""
    client = redis.Redis.from_url(redis_url)
    if client.connection_pool.connection_kwargs.get("db") == TEST_DB:
        client.flushdb()
    yield client
    client.close()


@pytest.fixture
def name() -> str:
    """A unique stream name for the test."""
    return f"t-{uuid.uuid4().hex[:10]}"


@pytest.fixture
def make_broker(redis_url: str, r: "redis.Redis") -> Iterator[Callable[..., Broker]]:
    """Factory for brokers. Consumer threads are always stopped on teardown."""
    created = []

    def factory(**kwargs) -> Broker:
        broker = Broker(redis_url, **kwargs)
        created.append(broker)
        return broker

    yield factory
    for broker in created:
        for sub in broker.subscribers:
            sub.stop()
        for sub in broker.subscribers:
            sub.join(10)
        broker.client.close()


@pytest.fixture
def broker(make_broker: Callable[..., Broker]) -> Broker:
    return make_broker()
