# Examples

Every example here is a complete script that was run against a real Redis, and the output shown is what it printed. To run one yourself, change the Redis URL to match your setup and `pip install rillkit` (plus `"rillkit[pydantic]"` where noted).

Most scripts use `start()` and `stop()` with a short sleep so they finish by themselves. In a real service you would call `broker.run()` instead (see [Lifecycle](/guide/lifecycle)), and you would use the default `block_ms` and `claim_idle_ms`. The scripts use short values so the retry behaviour is visible in seconds.

| Example | Shows |
| --- | --- |
| [Basic worker](/examples/basic-worker) | the smallest useful consumer, with the `Message` object |
| [Two-stage pipeline](/examples/pipeline) | `@subscribe` plus `@publisher`: extraction, then feature engineering |
| [Pydantic models](/examples/pydantic-models) | typed handlers and validation failures in the DLQ |
| [Retries and DLQ](/examples/retries-and-dlq) | flaky and broken messages, dead letters, `replay_dlq` |
| [Reject vs nack](/examples/reject-vs-nack) | `nack()` to retry, `reject()` to skip retries and dead-letter |
| [Manual ack](/examples/manual-ack) | `AckPolicy.MANUAL` with `ack()` and `nack()` |
| [Timing and idempotency](/examples/middleware-timing-and-idempotency) | a timing middleware and `Idempotent` |
| [Multiple workers](/examples/multiple-workers) | several consumers sharing a group, `active_workers` |
| [Graceful shutdown](/examples/graceful-shutdown) | SIGTERM, systemd and Docker |
| [FastAPI publisher](/examples/fastapi-publisher) | publishing from a web endpoint |
| [Migrating from redis-py](/examples/migrating-from-raw-redis-py) | a hand-rolled `XREADGROUP` loop, before and after |

The examples use stream names like `orders`, `jobs` and `tasks`. Use your own names, and a separate Redis database while experimenting.
