# Graceful shutdown

`broker.run()` handles `SIGINT` and `SIGTERM`: it finishes the message in flight, runs your shutdown hooks and exits with status 0. A second signal exits at once.

```python [graceful.py]
import logging
import time

from rillkit import Broker, Stream

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

broker = Broker.from_env()


@broker.on_shutdown
def flush():
    logging.info("flushing buffers")


@broker.subscribe(Stream("reports", group="renderers"), consumer="renderer-1", block_ms=1000)
def render(report: dict):
    logging.info("rendering report %s (takes 3 s)", report["id"])
    time.sleep(3)
    logging.info("finished report %s", report["id"])


if __name__ == "__main__":
    broker.publish("reports", {"id": 1})
    broker.publish("reports", {"id": 2})
    broker.run()
```

This run sent `SIGTERM` 1.5 seconds after start, while report 1 was being rendered:

```text
12:57:25 INFO consumer started | stream: reports | group: renderers | consumer: renderer-1 | policy: nack_on_error | max retries: 3
12:57:25 INFO rendering report 1 (takes 3 s)
12:57:26 INFO shutdown requested, finishing the current message before exiting
12:57:28 INFO finished report 1
12:57:28 INFO consumer stopped | stream: reports | consumer: renderer-1
12:57:28 INFO flushing buffers
exit code: 0
```

- `shutdown requested` appeared right after the signal, but the handler was **allowed to finish** report 1 (`finished report 1`) before the consumer stopped.
- `on_shutdown` (`flushing buffers`) ran after the consumer stopped, while the Redis client was still open.
- Report 2 had already been fetched in the same batch. It was not started, and stays pending until another worker claims it after `claim_idle_ms`. Use a small `count` if you want quick handover.
- `exit code: 0` means the process shut down cleanly, which is what supervisors want to see.

::: tip Keep the stop timeout above your longest handler
The process manager must wait at least as long as your slowest handler plus up to `block_ms`, or it will `SIGKILL` the process mid-message. A killed message is not lost (it stays pending and is retried) but it is repeated work.
:::

## systemd

```ini
# /etc/systemd/system/reports-worker.service
[Unit]
Description=Report renderer
After=network-online.target redis.service

[Service]
ExecStart=/srv/app/.venv/bin/python -m app.worker
Environment=REDIS_URL=redis://localhost:6379/0
Restart=on-failure
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

`systemctl stop` sends `SIGTERM`, waits up to `TimeoutStopSec`, then sends `SIGKILL`. systemd's default stop signal is already `SIGTERM`.

## Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# exec form: python is PID 1 and receives SIGTERM directly
CMD ["python", "-m", "app.worker"]
```

Use the exec form of `CMD` (a JSON list), not the shell form, so `docker stop` delivers `SIGTERM` to Python instead of to a shell. `docker stop` waits 10 seconds by default; raise it with `docker stop -t 30` or `stop_grace_period: 30s` in Compose when handlers are slow.

::: warning
The systemd unit and Dockerfile above are standard patterns and were not executed as part of writing these docs. The signal handling itself was tested by sending a real `SIGTERM`, as shown in the output.
:::
