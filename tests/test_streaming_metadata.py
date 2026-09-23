import os
import sqlite3
import tempfile

os.environ.setdefault("POSTGRES_DSN", f"sqlite://{tempfile.mkdtemp()}/t.sqlite")
from mrp import metadata


def _event(rid, source="stream"):
    return {
        "event_id": "a" * 32, "event_ts": "2026-09-24T00:00:00+00:00",
        "render_id": rid, "formula_id": "polar_loom", "formula_hash": "b" * 64,
        "params_json": {"rings": 6}, "width": 48, "height": 48,
        "runtime_ms": 10, "checksum": "c" * 64,
        "storage_uri": "file:///x.png", "preview_uri": "file:///x_prev.png",
        "bytes_full": 2048, "bytes_preview": 1024, "ingest_source": source,
    }


def test_insert_event_and_dedup():
    metadata.init_db()
    e = _event("rid-1")
    metadata.insert_event(e)
    metadata.insert_event(e)
    p = metadata._sqlite_path()
    con = sqlite3.connect(p)
    n = con.execute("SELECT count(*) FROM render_events WHERE render_id=?", ("rid-1",)).fetchone()[0]
    assert n == 1
    row = con.execute("SELECT ingest_source FROM render_events WHERE render_id=?", ("rid-1",)).fetchone()
    assert row[0] == "stream"


def test_migration_adds_column():
    metadata.init_db()
    p = metadata._sqlite_path()
    con = sqlite3.connect(p)
    cols = {r[1] for r in con.execute("PRAGMA table_info(render_events)")}
    assert "ingest_source" in cols
