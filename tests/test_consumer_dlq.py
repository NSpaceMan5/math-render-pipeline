"""Unit tests for DLQ + retry — no Kafka required (fake producer)."""
import json
import os
import tempfile

os.environ.setdefault("POSTGRES_DSN", f"sqlite://{tempfile.mkdtemp()}/t.sqlite")

import pytest

pytest.importorskip("confluent_kafka")

from mrp.streaming import consumer as consumer_mod
from mrp.streaming.consumer import RenderConsumer


class _FakeProducer:
    def __init__(self):
        self.sent = []
    def produce(self, topic, value=None, key=None, callback=None):
        self.sent.append((topic, value))
    def poll(self, timeout):
        pass
    def flush(self, timeout=None):
        pass


def _make():
    c = RenderConsumer.__new__(RenderConsumer)
    c._topic = "render.events"
    c._dlq_topic = "render.events.dlq"
    c._max_retries = 2
    c._backoff_base = 0.0
    c._dlq = _FakeProducer()
    c._running = True
    c._stats = {"ok": 0, "dlq": 0, "retries": 0, "skipped": 0}
    return c


def test_to_dlq_publishes_metadata():
    c = _make()
    c._to_dlq(b'{"broken":', "parse: bad json", 1, cid="abc123")
    assert len(c._dlq.sent) == 1
    topic, value = c._dlq.sent[0]
    assert topic == "render.events.dlq"
    payload = json.loads(value.decode("utf-8"))
    assert payload["error"] == "parse: bad json"
    assert payload["attempts"] == 1
    assert payload["correlation_id"] == "abc123"
    assert payload["original_topic"] == "render.events"
    assert c._stats["dlq"] == 1


def test_insert_with_retry_succeeds_second_attempt(monkeypatch):
    c = _make()
    calls = {"n": 0}

    def flaky(event):
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("boom")

    monkeypatch.setattr(consumer_mod.metadata, "insert_event", flaky)
    c._insert_with_retry({"render_id": "x"}, cid="cid")
    assert calls["n"] == 2
    assert c._stats["retries"] == 1


def test_insert_with_retry_raises_after_max(monkeypatch):
    c = _make()
    monkeypatch.setattr(consumer_mod.metadata, "insert_event",
                        lambda e: (_ for _ in ()).throw(RuntimeError("nope")))
    with pytest.raises(RuntimeError):
        c._insert_with_retry({"render_id": "x"}, cid="cid")
    assert c._stats["retries"] == c._max_retries
