import json
import re

import pytest

from helpers import entries
from rillkit import Broker, PublishError, Stream


def test_publish_returns_id_and_writes_json(broker: Broker, r, name):
    entry_id = broker.publish(name, {"a": 1})
    assert re.fullmatch(r"\d+-\d+", entry_id)
    [(stored_id, fields)] = entries(r, name)
    assert stored_id == entry_id
    assert json.loads(fields["data"]) == {"a": 1}


def test_publish_accepts_stream_object(broker: Broker, r, name):
    broker.publish(Stream(name, group="g"), [1, 2])
    assert json.loads(entries(r, name)[0][1]["data"]) == [1, 2]


def test_publish_per_call_maxlen_trims(broker: Broker, r, name):
    for i in range(500):
        broker.publish(name, {"i": i}, maxlen=10)
    # approximate trimming drops whole nodes, so the stream is short but not exactly 10
    assert 10 <= r.xlen(name) < 500


def test_stream_level_maxlen_trims(broker: Broker, r, name):
    stream = Stream(name, maxlen=10)
    for i in range(500):
        broker.publish(stream, {"i": i})
    assert 10 <= r.xlen(name) < 500


def test_publish_without_maxlen_keeps_everything(broker: Broker, r, name):
    for i in range(150):
        broker.publish(name, {"i": i})
    assert r.xlen(name) == 150


def test_publisher_object_publishes_with_its_maxlen(broker: Broker, r, name):
    pub = broker.publisher(name, maxlen=10)
    for i in range(500):
        pub.publish({"i": i})
    assert 10 <= r.xlen(name) < 500


def test_publish_unserialisable_body_raises_publish_error(broker: Broker, name):
    circular: list = []
    circular.append(circular)
    with pytest.raises(PublishError):
        broker.publish(name, circular)


def test_publish_redis_failure_raises_publish_error(broker: Broker, r, name):
    r.set(name, "not a stream")
    with pytest.raises(PublishError):
        broker.publish(name, {"a": 1})


def test_stream_dlq_name_default_and_override():
    assert Stream("orders").dlq_name == "orders-dlq"
    assert Stream("orders", dlq="dead").dlq_name == "dead"


def test_stream_is_frozen_and_group_optional():
    s = Stream("orders")
    assert s.group is None
    with pytest.raises(AttributeError):
        s.name = "x"  # type: ignore[misc]


def test_exact_maxlen_trimming(broker, r, name):
    for i in range(30):
        broker.publish(name, {"i": i}, maxlen=5, approximate=False)
    assert r.xlen(name) == 5
