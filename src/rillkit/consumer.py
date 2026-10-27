import inspect
import logging
import os
import socket
import threading
import time
from collections.abc import Sequence
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Optional,
    get_type_hints,
)

import redis

from .ack import AckPolicy
from .exceptions import AckMessage, DecodeError, NackMessage
from .message import Message
from .middleware import BaseMiddleware
from .stream import Stream

if TYPE_CHECKING:
    from .broker import Broker

log = logging.getLogger("rillkit")

RETRY_BACKOFF_SECONDS = 5
HEARTBEAT_PREFIX = "rillkit:workers:"


def _text(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else value


def _fields(raw: dict[Any, Any]) -> dict[str, str]:
    return {_text(k): _text(v) for k, v in raw.items()}


def _is_model(annotation: Any) -> bool:
    return inspect.isclass(annotation) and hasattr(annotation, "model_validate")


def _plan(handler: Callable[..., Any]) -> list[tuple[str, str, Any]]:
    """Decide what each handler parameter receives: the ``Message``, the plain body, or a model."""
    try:
        hints = get_type_hints(handler)
    except Exception:
        hints = getattr(handler, "__annotations__", {})
    plan: list[tuple[str, str, Any]] = []
    bodies = 0
    for name, param in inspect.signature(handler).parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        ann = hints.get(name, param.annotation)
        if ann is Message or (ann is param.empty and name in ("msg", "message")):
            plan.append((name, "message", None))
        elif _is_model(ann):
            plan.append((name, "model", ann))
            bodies += 1
        else:
            plan.append((name, "body", None))
            bodies += 1
    if bodies > 1:
        raise TypeError(f"{handler!r} takes more than one body parameter")
    return plan


class Subscriber:
    """Runs one consumer loop for one stream and group: claim stuck messages, then read new ones."""

    def __init__(
        self,
        broker: "Broker",
        stream: Stream,
        handler: Callable[..., Any],
        *,
        ack_policy: AckPolicy = AckPolicy.NACK_ON_ERROR,
        max_retries: Optional[int] = 3,
        claim_idle_ms: int = 60_000,
        backoff: float = 1.0,
        max_backoff_ms: int = 15 * 60_000,
        block_ms: int = 5000,
        count: int = 10,
        middlewares: Sequence[BaseMiddleware] = (),
        consumer: Optional[str] = None,
        heartbeat: bool = True,
        heartbeat_ttl: int = 60,
        group_start_id: str = "0",
    ) -> None:
        if not stream.group:
            raise ValueError(f"stream {stream.name!r} needs a group to be consumed")
        self.broker = broker
        self.stream = stream
        self.group: str = stream.group
        self.handler = handler
        self.ack_policy = AckPolicy(ack_policy)
        self.max_retries = max_retries
        self.claim_idle_ms = claim_idle_ms
        self.backoff = backoff
        self.max_backoff_ms = max_backoff_ms
        self.block_ms = block_ms
        self.count = count
        self.own_middlewares = list(middlewares)
        self.consumer = consumer or f"{stream.group}-{socket.gethostname()}-{os.getpid()}"
        self.heartbeat = heartbeat
        self.heartbeat_ttl = heartbeat_ttl
        self.group_start_id = group_start_id
        self._plan = _plan(handler)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def client(self) -> "redis.Redis":
        return self.broker.client

    @property
    def middlewares(self) -> list[BaseMiddleware]:
        """Broker-wide middleware first (outermost), then this subscriber's own."""
        return [*self.broker.middlewares, *self.own_middlewares]

    @property
    def heartbeat_key(self) -> str:
        return f"{HEARTBEAT_PREFIX}{self.stream.name}:{self.group}:{self.consumer}"

    # lifecycle

    def setup(self) -> None:
        try:
            self.client.xgroup_create(
                self.stream.name, self.group, id=self.group_start_id, mkstream=True
            )
            log.debug("created group %s on %s", self.group, self.stream.name)
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name=f"rillkit-{self.stream.name}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def _run(self) -> None:
        log.info(
            "consumer started | stream: %s | group: %s | consumer: %s | policy: %s"
            " | max retries: %s",
            self.stream.name, self.group, self.consumer, self.ack_policy.value,
            self.max_retries,
        )
        try:
            while not self._stop.is_set():
                self._beat()
                try:
                    for msg in self._claim():
                        self._process(msg)
                    for msg in self._read():
                        if self._stop.is_set():
                            break  # unread leftovers stay pending, claimed after the idle time
                        self._process(msg)
                except redis.exceptions.ResponseError as e:
                    if "NOGROUP" in str(e):
                        self.setup()
                    else:
                        self._loop_error(e)
                except Exception as e:  # redis or other loop-level error: keep the worker alive
                    self._loop_error(e)
        finally:
            if self.heartbeat:
                try:
                    self.client.delete(self.heartbeat_key)
                except Exception as e:
                    log.error("could not remove heartbeat key: %s", e)
            log.info(
                "consumer stopped | stream: %s | consumer: %s", self.stream.name, self.consumer
            )

    def _loop_error(self, e: Exception) -> None:
        log.error("consumer loop error, retrying in %s s: %s", RETRY_BACKOFF_SECONDS, e)
        self._stop.wait(RETRY_BACKOFF_SECONDS)

    def _beat(self) -> None:
        if not self.heartbeat:
            return
        try:
            self.client.set(self.heartbeat_key, int(time.time()), ex=self.heartbeat_ttl)
        except Exception as e:
            log.error("heartbeat failed: %s", e)

    # reading

    def _message(self, id: Any, raw: dict[Any, Any], deliveries: int) -> Message:
        return Message(_text(id), self.stream, _fields(raw), deliveries, self.consumer, self.client)

    def _read(self) -> list[Message]:
        result: Any = self.client.xreadgroup(
            self.group, self.consumer, {self.stream.name: ">"},
            count=self.count, block=self.block_ms,
        )
        return [self._message(i, f, 1) for _, entries in result or [] for i, f in entries]

    def _required_idle_ms(self, times_delivered: int) -> float:
        wait = self.claim_idle_ms * (self.backoff ** max(times_delivered - 1, 0))
        return min(wait, self.max_backoff_ms)

    def _exhausted(self, deliveries: int) -> bool:
        return self.max_retries is not None and deliveries > self.max_retries

    def _claim(self) -> list[Message]:
        """Take over pending messages idle long enough, honouring the retry backoff."""
        pending: Any = self.client.xpending_range(
            self.stream.name, self.group, "-", "+", self.count, idle=self.claim_idle_ms
        )
        due = {
            _text(p["message_id"]): p["times_delivered"]
            for p in pending
            if p["time_since_delivered"] >= self._required_idle_ms(p["times_delivered"])
        }
        if not due:
            return []
        claimed: Any = self.client.xclaim(
            self.stream.name, self.group, self.consumer, self.claim_idle_ms, list(due)
        )
        messages = []
        for id, raw in claimed:
            if raw is None:  # entry was trimmed from the stream while pending
                self.client.xack(self.stream.name, self.group, id)
                continue
            attempts = due[_text(id)]
            if self._exhausted(attempts):
                # not run again, so the delivery count is the attempts it already had
                self._dead_letter(self._message(id, raw, attempts), "retries exhausted")
                continue
            msg = self._message(id, raw, attempts + 1)
            messages.append(msg)
        return messages

    # processing

    def _invoke(self, msg: Message) -> Any:
        kwargs: dict[str, Any] = {}
        for name, kind, model in self._plan:
            if kind == "message":
                kwargs[name] = msg
            elif kind == "model":
                try:
                    kwargs[name] = model.model_validate(msg.body)
                except DecodeError:
                    raise
                except Exception as e:
                    raise DecodeError(f"body failed validation: {e}") from e
            else:
                kwargs[name] = msg.body
        result = self.handler(**kwargs)
        publishers = getattr(self.handler, "_rillkit_publishers", ())
        if result is not None:
            for publisher in publishers:
                publisher.publish(result)
        return result

    def _chain(self) -> Callable[[Message], Any]:
        call = self._invoke
        for mw in reversed(self.middlewares):
            call = partial(mw.consume_scope, call)
        return call

    def _process(self, msg: Message) -> None:
        policy = self.ack_policy
        exc: Optional[BaseException] = None
        if policy is AckPolicy.ACK_FIRST:
            msg.ack()
        try:
            for mw in self.middlewares:
                mw.on_receive(msg)
            self._chain()(msg)
        except AckMessage:
            msg.ack()
        except NackMessage as e:
            msg.nack()
            exc = e
        except DecodeError as e:
            log.error("message %s cannot be decoded, sending to DLQ: %s", msg.id, e)
            exc = e
            self._dead_letter(msg, str(e))
        except Exception as e:
            log.error("handler failed for message %s (delivery %s): %s", msg.id, msg.deliveries, e)
            exc = e
            msg.error = e
            if policy is AckPolicy.ACK_ALWAYS:
                msg.ack()
            elif policy in (AckPolicy.NACK_ON_ERROR, AckPolicy.MANUAL):
                msg.nack()
        else:
            if policy in (AckPolicy.NACK_ON_ERROR, AckPolicy.ACK_ALWAYS) and not msg.nacked:
                msg.ack()

        if msg.nacked and not msg.acked and self._exhausted(msg.deliveries):
            self._dead_letter(msg, (str(exc) or type(exc).__name__) if exc else "nacked")
        self._after(msg, exc)
        self._beat()

    def _after(self, msg: Message, exc: Optional[BaseException]) -> None:
        for mw in self.middlewares:
            try:
                mw.after_processed(msg, exc)
            except Exception as e:
                log.error("after_processed failed in %s: %s", type(mw).__name__, e)

    def _dead_letter(self, msg: Message, error: str) -> None:
        """Copy the entry to the DLQ stream with context, then ack it so it stops being retried."""
        log.warning("moving message %s to %s: %s", msg.id, self.stream.dlq_name, error)
        entry: dict[Any, Any] = dict(msg.raw)
        entry.update({
            "x-original-id": msg.id,
            "x-stream": self.stream.name,
            "x-group": self.group,
            "x-error": error[:1000],
            "x-deliveries": str(msg.deliveries),
        })
        pipe = self.client.pipeline()
        pipe.xadd(self.stream.dlq_name, entry)
        pipe.xack(self.stream.name, self.group, msg.id)
        pipe.execute()
        msg.acked = True
        msg.nacked = False
