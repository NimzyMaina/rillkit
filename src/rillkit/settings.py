import os
from dataclasses import dataclass
from typing import Optional

import redis


@dataclass
class Settings:
    """Connection settings.

    ``Settings.from_env()`` reads REDIS_URL, or REDIS_HOST/PORT/DB/PASSWORD/SSL.
    """

    url: Optional[str] = None
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False

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
        )

    def client(self) -> "redis.Redis":
        if self.url:
            return redis.Redis.from_url(self.url)
        return redis.Redis(
            host=self.host, port=self.port, db=self.db, password=self.password, ssl=self.ssl
        )
