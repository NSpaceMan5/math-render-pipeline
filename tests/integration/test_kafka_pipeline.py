"""
End-to-end: producer publishes, consumer reads, metadata records.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

pytestmark = pytest.mark.integration


def _bind_dsn(dsn: str, tmp_path):
    """Mutate mrp settings in place (see test_postgres_roundtrip)."""
    from mrp import config, metadata
    config.settings.postgres_dsn = dsn
    config.settings.parquet_root = str(tmp_path / "parquet")
    config.settings.artifact_root = str(tmp_path / "renders")
    config.settings.use_s3 = False
    return metadata


def _wait_for_broker(bootstrap: str, timeout: float = 30.0) -> None:
    """Block until the Kafka broker is reachable, or raise TimeoutError."""
    from confluent_kafka.admin import AdminClient
    admin = AdminClient({"bootstrap.servers": bootstrap})
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            md = admin.list_topics(timeout=5.0)
            if md.brokers:
                return
        except Exception as e:
            last_err = e
        time.sleep(1.0)
    raise TimeoutError(f"broker {bootstrap} not ready after {timeout}s "
                       f"(last error: {last_err})")


def test_produce_consume_roundtrip(redpanda_container, tmp_path):
    bootstrap = redpanda_container.get_bootstrap_server()
    _wait_for_broker(bootstrap)

    dsn = f"sqlite:///{tmp_path / 'm.sqlite'}"
    meta = _bind_dsn(dsn, tmp_path)
    meta.init_db()

    from mrp.streaming import RenderConsumer, RenderProducer
    from mrp.streaming.schemas import TOPIC

    producer = RenderProducer(bootstrap, TOPIC)

    event = {
        "event_id": "e" * 32,
        "event_ts": "2026-09-25T00:00:00+00:00",
        "render_id": "kafka-rid-1",
        "formula_id": "polar_loom",
        "formula_hash": "f" * 64,
        "params_json": {"rings": 6},
        "width": 64, "height": 48, "runtime_ms": 8,
        "checksum": "a" * 64,
        "storage_uri": "file:///x.png",
        "preview_uri": "file:///x_prev.png",
        "bytes_full": 2048, "bytes_preview": 1024,
        "ingest_source": "stream",
    }
    producer.publish(event)
    producer.flush(timeout=5.0)

    consumer = RenderConsumer(bootstrap, TOPIC, "test-group",
                              dlq_topic=TOPIC + ".dlq", max_retries=2)
    stats = consumer.run(max_messages=1, timeout=5.0)
    assert stats["ok"] == 1

    con = sqlite3.connect(str(tmp_path / "m.sqlite"))
    n = con.execute(
        "SELECT count(*) FROM render_events WHERE render_id=?",
        (event["render_id"],),
    ).fetchone()[0]
    assert n == 1
