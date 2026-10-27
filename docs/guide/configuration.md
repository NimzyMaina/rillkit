# Configuration

A `Broker` needs a Redis connection. There are four ways to give it one.

## A URL

```python
broker = Broker("redis://localhost:6379/0")
broker = Broker("redis://:secret@redis.internal:6379/2")
```

With no arguments, `Broker()` connects to `localhost:6379`, db 0.

## Settings

[`Settings`](/reference/settings) is a dataclass with `url`, `host`, `port`, `db`, `password` and `ssl`:

```python
from rillkit import Broker, Settings

broker = Broker(settings=Settings(host="redis.internal", port=6380, db=2, password="secret", ssl=True))
```

If `url` is set, it wins and the other fields are ignored.

## Environment variables

`Broker.from_env()` (or `Settings.from_env()`) reads:

| Variable | Default | Notes |
| --- | --- | --- |
| `REDIS_URL` | none | If set, takes priority over everything below |
| `REDIS_HOST` | `localhost` | |
| `REDIS_PORT` | `6379` | converted to `int` |
| `REDIS_DB` | `0` | converted to `int` |
| `REDIS_PASSWORD` | none | |
| `REDIS_SSL` | off | `1`, `true` or `yes` (any case) turn TLS on |

Pass a different prefix to read, say, `MYAPP_REDIS_URL`:

```python [g_config.py]
import os

from rillkit import Settings, Broker

os.environ.update(REDIS_HOST="localhost", REDIS_PORT="6390", REDIS_DB="14", REDIS_SSL="false")
s = Settings.from_env()
print(s)
print(Broker.from_env().client.ping())
os.environ.update(MYAPP_REDIS_URL="redis://localhost:6390/14")
print(Settings.from_env("MYAPP_REDIS_"))
print(Broker(settings=Settings.from_env("MYAPP_REDIS_")).client.ping())

import redis
own = redis.Redis(host="localhost", port=6390, db=14, decode_responses=False, socket_timeout=10)
print(Broker(client=own).client is own)
```

```text
Settings(url='redis://localhost:6390/14', host='localhost', port=6390, db=14, password=None, ssl=False)
True
Settings(url='redis://localhost:6390/14', host='localhost', port=6379, db=0, password=None, ssl=False)
True
True
```

(In this run `REDIS_URL` was also set in the environment, which is why the first `Settings` shows a `url`.)

`Broker.from_env(prefix="REDIS_", **kwargs)` forwards extra keyword arguments such as `middlewares=[...]` to `Broker`.

## TLS and managed Redis (Upstash and friends)

Hosted services usually require TLS. Either use a `rediss://` URL (note the double s), or set `ssl`:

::: code-group
```bash [Environment]
export REDIS_URL="rediss://default:YOUR_PASSWORD@eu1-example-12345.upstash.io:6379"
```
```bash [Host and port]
export REDIS_HOST=eu1-example-12345.upstash.io
export REDIS_PORT=6379
export REDIS_PASSWORD=YOUR_PASSWORD
export REDIS_SSL=true
```
```python [In code]
broker = Broker("rediss://default:YOUR_PASSWORD@eu1-example-12345.upstash.io:6379")
```
:::

::: warning Blocking reads and server timeouts
rillkit blocks in `XREADGROUP` for up to `block_ms` (5 seconds by default). Some managed Redis proxies close idle connections or limit command duration. If you see repeated connection errors in the logs, lower `block_ms` and check the provider's idle timeout. rillkit logs the error and retries after 5 seconds rather than crashing.
:::

## Bring your own client

Pass any `redis.Redis` you have configured (timeouts, retries, custom pools, Sentinel, and so on):

```python
import redis
from rillkit import Broker

client = redis.Redis(host="redis.internal", socket_timeout=10, health_check_interval=30)
broker = Broker(client=client)
```

rillkit works with both `decode_responses=False` (the default) and `True`. Two cautions:

- Do not set `socket_timeout` lower than `block_ms`, or blocking reads will time out. (redis-py extends nothing for you here.)
- `broker.stop()` closes the client, so do not share a client you still need afterwards.
