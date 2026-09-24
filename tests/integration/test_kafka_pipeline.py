"""
End-to-end: producer publishes, consumer reads, metadata records.

Requires Docker (Redpanda container). Skipped otherwise.
"""
from __future__ import annotations

import importlib
import os
import sqlite3

import pytest


pytestmark = pytest.mark.integration


def _reload_metadata(dsn: str, tmp_path):
    os.environ["POSTGRES_DSN"] = dsn
    os.environ["PARQUET_ROOT"] = str(tmp_path / "parquet")
    os.environ["ARTIFACT_ROOT"] = str(tmp_path / "renders")
    os.environ["USE_S3"] = "false"

    import mrp.config
    importlib.reload(mrp.config)
    import mrp.storage
    importlib.reload(mrp.storage)
    import mrp.metadata
    importlib.reload(mrp.metadata)
    return mrp.metadata


def test_produce_consume_roundtrip(redpanda_container, tmp_path):
    bootstrap = redpanda_container.get_bootstrap_server()

    meta = _reload_metadata("sqlite://" + str(tmp_path / "m.sqlite"), tmp_path)
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
    producer.flush()

    consumer = RenderConsumer(bootstrap, TOPIC, "test-group",
                              dlq_topic=TOPIC + ".dlq", max_retries=2)
    stats = consumer.run(max_messages=1)
    assert stats["ok"] == 1

    con = sqlite3.connect(str(tmp_path / "m.sqlite"))
    n = con.execute(
        "SELECT count(*) FROM render_events WHERE render_id=?",
        (event["render_id"],),
    ).fetchone()[0]
    assert n == 1
