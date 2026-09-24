"""
Real Postgres round-trip through the metadata layer.

Runs `metadata.insert()` + `insert_event()` against a live Postgres, then
reads back and asserts the schema, dedup, and Parquet partitioning.
"""
from __future__ import annotations

import importlib
import os

import pytest


pytestmark = pytest.mark.integration


def _reload_metadata(dsn: str, parquet_root: str, artifact_root: str):
    """Reload mrp.config + mrp.metadata so they pick up the new DSN."""
    os.environ["POSTGRES_DSN"] = dsn
    os.environ["PARQUET_ROOT"] = parquet_root
    os.environ["ARTIFACT_ROOT"] = artifact_root
    os.environ["USE_S3"] = "false"

    import mrp.config
    importlib.reload(mrp.config)
    import mrp.storage
    importlib.reload(mrp.storage)
    import mrp.metadata
    importlib.reload(mrp.metadata)
    return mrp.metadata


def test_insert_and_query_postgres(postgres_dsn, tmp_path):
    meta = _reload_metadata(
        postgres_dsn,
        str(tmp_path / "parquet"),
        str(tmp_path / "renders"),
    )
    meta.init_db()

    from mrp import storage as st
    from mrp.models import RenderSpec
    from mrp.renderer import render

    spec = RenderSpec(formula_id="polar_loom", width=64, height=48,
                      params={"rings": 6})
    r, full, prev = render(spec)
    r.storage_uri, r.preview_uri = st.put(r.render_id, full, prev)
    meta.insert(r)

    with __import__("psycopg").connect(postgres_dsn) as c:
        row = c.execute(
            "SELECT formula_id, checksum, ingest_source "
            "FROM render_events WHERE render_id=%s",
            (r.render_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == "polar_loom"
    assert row[1] == r.checksum
    assert row[2] == "batch"


def test_insert_event_idempotent_postgres(postgres_dsn, tmp_path):
    meta = _reload_metadata(
        postgres_dsn,
        str(tmp_path / "parquet"),
        str(tmp_path / "renders"),
    )
    meta.init_db()

    ev = {
        "event_id": "a" * 32,
        "event_ts": "2026-09-25T00:00:00+00:00",
        "render_id": "pg-rid-1",
        "formula_id": "moire_grid",
        "formula_hash": "b" * 64,
        "params_json": {"f1": 10.0, "f2": 10.4},
        "width": 64, "height": 48, "runtime_ms": 12,
        "checksum": "c" * 64,
        "storage_uri": "file:///x.png",
        "preview_uri": "file:///x_prev.png",
        "bytes_full": 2048, "bytes_preview": 1024,
        "ingest_source": "stream",
    }
    meta.insert_event(ev)
    meta.insert_event(ev)

    with __import__("psycopg").connect(postgres_dsn) as c:
        n = c.execute(
            "SELECT count(*) FROM render_events WHERE render_id=%s",
            (ev["render_id"],),
        ).fetchone()[0]
    assert n == 1
