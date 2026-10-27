# Broker

```python
from rillkit import Broker, Publisher
```

`Broker` owns the Redis client, the subscribers and the lifecycle hooks.

## Constructor

```python
Broker(
    url: Optional[str] = None,
    *,
    client: Optional[redis.Redis] = None,
    settings: Optional[Settings] = None,
    middlewares: Sequence[BaseMiddleware] = (),
)
```

| Parameter | Default | Description |
| --- | --- | --- |
| `url` | `None` | Redis URL, used if neither `client` nor `settings` is given. With none of the three, it connects to `localhost:6379`, db 0. |
| `client` | `None` | An existing `redis.Redis`. Takes priority over `settings` and `url`. |
| `settings` | `None` | A [`Settings`](/reference/settings) object. Takes priority over `url`. |
| `middlewares` | `()` | Broker-wide [middleware](/reference/middleware), added in order with `use()`. |

Attributes: `client` (the Redis client), `middlewares` (list), `subscribers` (list of registered subscribers).

### `Broker.from_env`

```python
Broker.from_env(prefix: str = "REDIS_", **kwargs) -> Broker
```

Builds `Settings.from_env(prefix)` and passes it as `settings=`. Extra keyword arguments (for example `middlewares=[...]`) go to the constructor.

## Registering

### `subscribe`

```python
Broker.subscribe(
    stream: Union[str, Stream],
    *,
    group: Optional[str] = None,
    ack_policy: AckPolicy = AckPolicy.NACK_ON_ERROR,
    max_retries: Optional[int] = 3,
    claim_idle_ms: int = 60_000,
    backoff: float = 1.0,
    max_backoff_ms: int = 900_000,
    block_ms: int = 5000,
    count: int = 10,
    middlewares: Sequence[BaseMiddleware] = (),
    consumer: Optional[str] = None,
    heartbeat: bool = True,
    heartbeat_ttl: int = 60,
    group_start_id: str = "0",
) -> Callable[[Callable], Callable]
```

A decorator factory. The decorated function is returned unchanged. Raises `ValueError` if there is no group (neither on the `Stream` nor in `group`) and `TypeError` if the handler has more than one body parameter.

| Parameter | Default | Description |
| --- | --- | --- |
| `stream` | required | Stream name or `Stream`. |
| `group` | `None` | Consumer group. If given, it replaces `Stream.group`; the stream's name, `dlq`, `maxlen` and `codec` are kept. |
| `ack_policy` | `NACK_ON_ERROR` | See [AckPolicy](/reference/ack-policy). Plain strings such as `"manual"` are accepted too. |
| `max_retries` | `3` | Retries after the first attempt (total attempts `max_retries + 1`). `None` means no limit. |
| `claim_idle_ms` | `60000` | Idle time before a pending message is retried. Must exceed your slowest handler. |
| `backoff` | `1.0` | Multiplier per retry: required idle = `min(claim_idle_ms * backoff ** (deliveries - 1), max_backoff_ms)`. |
| `max_backoff_ms` | `900000` | Cap on the required idle time (15 minutes). |
| `block_ms` | `5000` | Milliseconds one `XREADGROUP` blocks. |
| `count` | `10` | Entries per read and pending entries inspected per claim pass. |
| `middlewares` | `()` | Middleware for this subscriber only, inside the broker-wide ones. |
| `consumer` | `<group>-<hostname>-<pid>` | Consumer name. |
| `heartbeat` | `True` | Write a heartbeat key. |
| `heartbeat_ttl` | `60` | Heartbeat key TTL in seconds. |
| `group_start_id` | `"0"` | Start position for a newly created group. `"$"` means only new entries. |

See [Consuming](/guide/consuming) for handler signature rules.

### `publisher`

```python
Broker.publisher(stream: Union[str, Stream], *, maxlen: Optional[int] = None) -> Publisher
```

Returns a `Publisher`. Used as a decorator it publishes the handler's non-`None` return value to `stream`. Decorators stack.

### `use`

```python
Broker.use(middleware: BaseMiddleware) -> BaseMiddleware
```

Adds broker-wide middleware, sets `middleware.broker`, and returns the middleware.

## Publishing

```python
Broker.publish(stream: Union[str, Stream], body: Any, *, maxlen: Optional[int] = None, approximate: bool = True) -> str
```

Adds one entry (`XADD`, field `data` = JSON) and returns its id. `maxlen` defaults to `Stream.maxlen`. Trimming is approximate by default (`XADD MAXLEN ~`), which Redis applies in whole macro-nodes, so streams shorter than about 100 entries are effectively never trimmed. Pass `approximate=False` for an exact cap. The call goes through every broker-wide middleware's `publish_scope`. Raises [`PublishError`](/reference/exceptions) if Redis fails or the body cannot be encoded.

## Lifecycle hooks

Each takes a function with no arguments, registers it and returns it, so it works as a decorator.

| Method | Runs |
| --- | --- |
| `on_startup(func)` | first in `start()`, before the connection check |
| `after_startup(func)` | after groups exist and consumer threads have started |
| `on_shutdown(func)` | in `stop()`, after consumers finish, before the client closes |
| `after_shutdown(func)` | last in `stop()`, after the client closes |

## Running

| Method | Description |
| --- | --- |
| `start() -> None` | Runs `on_startup` hooks, pings Redis, creates the groups (`XGROUP CREATE ... MKSTREAM`), starts one daemon thread per subscriber, runs `after_startup` hooks, and returns. |
| `stop(timeout: Optional[float] = None) -> None` | Asks consumers to stop, joins each thread for up to `timeout` seconds (`None` waits forever), runs `on_shutdown`, closes the client, runs `after_shutdown`. Safe to call more than once and from another thread: the shutdown work happens once per start. |
| `run(handle_signals: bool = True, shutdown_timeout: Optional[float] = None) -> None` | `start()`, then blocks until SIGINT or SIGTERM (first signal: graceful, second: `sys.exit(1)`), until `stop()` is called, or until all consumer threads have ended; then `stop(shutdown_timeout)`. Signal handlers are installed only from the main thread and the previous handlers are restored afterwards. |

## Operations

| Method | Description |
| --- | --- |
| `active_workers(stream, group: Optional[str] = None) -> list[str]` | Sorted consumer names that have a live heartbeat for the stream and group. `group` defaults to the `Stream`'s group. |
| `replay_dlq(stream, count: int = 100) -> int` | Moves up to `count` entries from the stream's DLQ back onto the stream, without the `x-` fields, deleting them from the DLQ. Returns how many were moved. Pass the **original** stream. |

## Publisher

```python
Publisher(broker: Broker, stream: Stream, maxlen: Optional[int] = None)
```

Returned by `broker.publisher(...)`.

| Member | Description |
| --- | --- |
| `broker`, `stream`, `maxlen` | the values it was created with |
| `__call__(func)` | decorator: records the publisher on `func` and returns `func` |
| `publish(body) -> str` | `broker.publish(self.stream, body, maxlen=self.maxlen)` |
