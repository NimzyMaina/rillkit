import os
from dataclasses import dataclass
from typing import Optional

import redis


def _seconds(value: Optional[str], default: Optional[float]) -> Optional[float]:
    if value is None or value == "":
        return default
    return None if value.strip().lower() in ("none", "off", "0") else float(value)


@dataclass
class Settings:
    """Connection settings.

    ``Settings.from_env()`` reads REDIS_URL, or REDIS_HOST/PORT/DB/PASSWORD/SSL, plus
    REDIS_SOCKET_TIMEOUT (seconds, or ``none``).

    ``socket_timeout`` is set explicitly because consumers block in ``XREADGROUP`` for up to
    ``block_ms`` and the client must wait longer than that. redis-py 8 changed its own default to
    5 s, which is shorter than rillkit's default block time.
    """

    url: Optional[str] = None
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    socket_timeout: Optional[float] = 15.0

    @classmethod
    def from_env(cls, prefix: str = "REDIS_") -> "Settings":
        env = os.environ
        return cls(
            url=env.get(f"{prefix}URL"),
            host=env.get(f"{prefix}HOST", "localhost"),
            port=int(env.get(f"{prefix}PORT", 6379)),
            db=int(env.get(f"{prefix}DB", 0)),
            password=env.get(f"{prefix}PASSWORD"),
            ssl=env.get(f"{prefix}SSL", "").lower() in ("1", "true", "yes"),
            socket_timeout=_seconds(env.get(f"{prefix}SOCKET_TIMEOUT"), 15.0),
        )

    def client(self) -> "redis.Redis":
        if self.url:
            return redis.Redis.from_url(self.url, socket_timeout=self.socket_timeout)
        return redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            ssl=self.ssl,
            socket_timeout=self.socket_timeout,
        )
