"""
Real Postgres round-trip through the metadata layer.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def _bind_dsn(dsn: str, tmp_path):
    """Point mrp at a fresh DSN without reloading modules.

    Reloading breaks module-level references (consumer / renderer hold a
    direct reference to `mrp.metadata`). Mutating settings in place keeps
    every module consistent within a single test process.
    """
    from mrp import config, metadata
    config.settings.postgres_dsn = dsn
    config.settings.parquet_root = str(tmp_path / "parquet")
    config.settings.artifact_root = str(tmp_path / "renders")
    config.settings.use_s3 = False
    return metadata


def test_insert_and_query_postgres(postgres_dsn, tmp_path):
    meta = _bind_dsn(postgres_dsn, tmp_path)
    meta.init_db()

    from mrp import storage as st
    from mrp.models import RenderSpec
    from mrp.renderer import render

    spec = RenderSpec(formula_id="polar_loom", width=64, height=48,
                      params={"rings": 6})
    r, full, prev = render(spec)
    r.storage_uri, r.preview_uri = st.put(r.render_id, full, prev)
    meta.insert(r)

    import psycopg
    with psycopg.connect(postgres_dsn) as c:
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
    meta = _bind_dsn(postgres_dsn, tmp_path)
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

    import psycopg
    with psycopg.connect(postgres_dsn) as c:
        n = c.execute(
            "SELECT count(*) FROM render_events WHERE render_id=%s",
            (ev["render_id"],),
        ).fetchone()[0]
    assert n == 1
