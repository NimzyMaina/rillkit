import pytest
import redis

from rillkit import Broker, Settings

KEYS = ["URL", "HOST", "PORT", "DB", "PASSWORD", "SSL"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in KEYS:
        monkeypatch.delenv(f"REDIS_{key}", raising=False)
        monkeypatch.delenv(f"MYAPP_{key}", raising=False)


def test_defaults():
    s = Settings.from_env()
    assert s == Settings(url=None, host="localhost", port=6379, db=0, password=None, ssl=False)


def test_url(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://example:1234/3")
    s = Settings.from_env()
    assert s.url == "redis://example:1234/3"
    kwargs = s.client().connection_pool.connection_kwargs
    assert (kwargs["host"], kwargs["port"], kwargs["db"]) == ("example", 1234, 3)


def test_host_port_db_password_ssl(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "cache.internal")
    monkeypatch.setenv("REDIS_PORT", "6390")
    monkeypatch.setenv("REDIS_DB", "7")
    monkeypatch.setenv("REDIS_PASSWORD", "s3cret")
    monkeypatch.setenv("REDIS_SSL", "true")
    s = Settings.from_env()
    assert s == Settings(
        url=None, host="cache.internal", port=6390, db=7, password="s3cret", ssl=True
    )
    pool = s.client().connection_pool
    assert pool.connection_kwargs["host"] == "cache.internal"
    assert pool.connection_kwargs["password"] == "s3cret"
    assert pool.connection_class is redis.SSLConnection


@pytest.mark.parametrize("value,expected", [("1", True), ("YES", True), ("True", True),
                                            ("0", False), ("false", False), ("", False)])
def test_ssl_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("REDIS_SSL", value)
    assert Settings.from_env().ssl is expected


def test_custom_prefix(monkeypatch):
    monkeypatch.setenv("MYAPP_HOST", "h")
    monkeypatch.setenv("MYAPP_PORT", "1")
    monkeypatch.setenv("REDIS_HOST", "ignored")
    s = Settings.from_env("MYAPP_")
    assert (s.host, s.port) == ("h", 1)


def test_broker_from_env_uses_url(monkeypatch, redis_url):
    monkeypatch.setenv("REDIS_URL", redis_url)
    broker = Broker.from_env()
    try:
        assert broker.client.ping()
    finally:
        broker.client.close()


def test_broker_accepts_url_client_and_settings(redis_url):
    client = redis.Redis.from_url(redis_url)
    assert Broker(client=client).client is client
    from_url = Broker(redis_url)
    from_settings = Broker(settings=Settings(url=redis_url))
    try:
        assert from_url.client.ping() and from_settings.client.ping()
    finally:
        from_url.client.close()
        from_settings.client.close()
        client.close()
