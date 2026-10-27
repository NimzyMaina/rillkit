# Settings

```python
from rillkit import Settings
```

```python
@dataclass
class Settings:
    url: Optional[str] = None
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
```

| Field | Default | Description |
| --- | --- | --- |
| `url` | `None` | A Redis URL (`redis://`, `rediss://`, `unix://`). If set, the other fields are ignored. |
| `host` | `"localhost"` | Server host. |
| `port` | `6379` | Server port. |
| `db` | `0` | Database number. |
| `password` | `None` | Password. |
| `ssl` | `False` | Use TLS. |

## `Settings.from_env`

```python
Settings.from_env(prefix: str = "REDIS_") -> Settings
```

Reads these environment variables, each prefixed with `prefix`:

| Variable | Maps to | Default if unset |
| --- | --- | --- |
| `<prefix>URL` | `url` | `None` |
| `<prefix>HOST` | `host` | `"localhost"` |
| `<prefix>PORT` | `port` (as `int`) | `6379` |
| `<prefix>DB` | `db` (as `int`) | `0` |
| `<prefix>PASSWORD` | `password` | `None` |
| `<prefix>SSL` | `ssl`: true for `1`, `true`, `yes` (any case) | `False` |

## `Settings.client`

```python
Settings.client() -> redis.Redis
```

Builds the client: `redis.Redis.from_url(url)` if `url` is set, otherwise `redis.Redis(host=..., port=..., db=..., password=..., ssl=...)`.

See [Configuration](/guide/configuration).
