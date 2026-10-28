# Consuming

```python
@broker.subscribe(Stream("orders", group="billing"))
def handle_order(order: dict):
    ...
```

`subscribe` registers the function and returns it unchanged. Each subscription runs its own consumer thread, and that thread handles **one message at a time**, in order. To process more in parallel, run more workers (see [Operations](/guide/operations#scaling)), not more threads.

## Subscribe options

| Option | Default | What it does |
| --- | --- | --- |
| `stream` | required | A stream name or a [`Stream`](/reference/stream). A consumer needs a group, from either `Stream.group` or `group=`. |
| `group` | `None` | Consumer group. Overrides `Stream.group` if both are given. Without any group, `subscribe` raises `ValueError`. |
| `ack_policy` | `AckPolicy.NACK_ON_ERROR` | When to acknowledge. See [Ack policies](/guide/ack-policies). Inside a handler, `msg.nack()` retries and `msg.reject()` skips retries and dead-letters. |
| `max_retries` | `3` | Retries after the first attempt, so up to `max_retries + 1` runs. `None` retries forever. |
| `claim_idle_ms` | `60000` | How long a pending message must sit idle before it is retried. Must be longer than your slowest handler. |
| `backoff` | `1.0` | Multiplier applied to the idle time on each further retry. `1.0` means constant. |
| `max_backoff_ms` | `900000` | Upper limit for the (backed-off) idle time. |
| `block_ms` | `5000` | How long one `XREADGROUP` waits for new entries. It is also the longest a stop request can wait. |
| `count` | `10` | Entries fetched per read, and pending entries inspected per claim pass. |
| `middlewares` | `()` | Middleware for this subscription only, run inside the broker-wide ones. |
| `consumer` | `<group>-<hostname>-<pid>` | Consumer name. Must be unique per running worker. |
| `heartbeat` | `True` | Write a heartbeat key so [`active_workers`](/guide/operations#heartbeat-and-active-workers) can see this worker. |
| `heartbeat_ttl` | `60` | Seconds before the heartbeat key expires. |
| `group_start_id` | `"0"` | Where a **new** group starts reading: `"0"` is the beginning of the stream, `"$"` is only entries added from now on. Ignored if the group already exists. |

## Handler signature rules

RillKit looks at your handler's parameters once, when you subscribe, and decides what to pass to each:

| Parameter | Receives |
| --- | --- |
| Annotated `Message` (any name) | the [`Message`](/reference/message) |
| Unannotated, named `msg` or `message` | the `Message` |
| Annotated with a pydantic model class | the body, validated into that model |
| Anything else | the decoded body (a `dict` for JSON objects) |

Extra rules:

- At most **one** body parameter. Two raise `TypeError` when the module is imported, not when the first message arrives.
- No parameters at all is allowed.
- `*args` and `**kwargs` are skipped.
- Parameters are passed by keyword, so order does not matter.

```python [g_consuming.py]
import logging
import time

from rillkit import Broker, Message, Stream

logging.basicConfig(level=logging.WARNING)
broker = Broker("redis://localhost:6379/0")
seen = []


@broker.subscribe("tasks", group="g1", consumer="c1", block_ms=200)
def by_name(msg):                      # an unannotated parameter named msg/message gets the Message
    seen.append(("msg", type(msg).__name__, msg.body))


@broker.subscribe(Stream("tasks", group="g2"), consumer="c2", block_ms=200)
def mixed(payload, m: Message):        # any name works if annotated with Message
    seen.append(("mixed", payload, m.deliveries))


@broker.subscribe(Stream("tasks", group="g3"), consumer="c3", block_ms=200)
def plain(anything):                   # a single other parameter receives the body
    seen.append(("plain", anything))


@broker.subscribe(Stream("tasks", group="g4"), consumer="c4", block_ms=200)
def nothing():                         # no parameters at all is fine
    seen.append(("nothing",))


def too_many(a, b): ...


for bad in (lambda: broker.subscribe("tasks")(lambda x: None),   # no group anywhere
            lambda: broker.subscribe("tasks", group="g")(too_many)):  # two body parameters
    try:
        bad()
    except Exception as e:
        print(type(e).__name__, e)

broker.start()
broker.publish("tasks", {"n": 1})
time.sleep(1)
broker.stop()
for s in sorted(seen, key=str):
    print(s)
```

```text
ValueError stream 'tasks' needs a group to be consumed
TypeError <function too_many at 0x109ba1bc0> takes more than one body parameter
('mixed', {'n': 1}, 1)
('msg', 'Message', {'n': 1})
('nothing',)
('plain', {'n': 1})
```

The body is whatever the JSON held. For a JSON object that is a `dict`. A producer that sends `[1, 2, 3]` gives you a `list`. You can annotate it `dict`, `list` or leave it bare; the annotation is not enforced unless it is a pydantic model.

## Return values

What a handler returns is ignored, unless it is decorated with [`@broker.publisher`](/guide/publishing#the-publisher-decorator), in which case a non-`None` return value is published.

## Where a new group starts

By default a new group begins at the start of the stream (`group_start_id="0"`), so a freshly deployed service processes the backlog. For "only things from now on", use `"$"`:

```python [g_start_id.py]
import time
from rillkit import Broker, Stream

broker = Broker("redis://localhost:6379/0")
broker.publish("tasks", {"before": True})
seen = []


@broker.subscribe(Stream("tasks", group="late"), consumer="c1", block_ms=200, group_start_id="$")
def h(task: dict):
    seen.append(task)


broker.start()
time.sleep(0.4)
broker.publish("tasks", {"after": True})
time.sleep(0.6)
broker.stop()
print(seen)
```

```text
[{'after': True}]
```

The message published before the group existed was skipped.
