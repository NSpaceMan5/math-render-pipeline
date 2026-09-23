import sqlite3
from pathlib import Path

from mrp import metadata, storage
from mrp.models import RenderSpec
from mrp.renderer import render


def _fresh_spec():
    return RenderSpec(formula_id="polar_loom", width=48, height=48, params={"rings": 6})


def test_init_and_insert():
    metadata.init_db()
    r, full, prev = render(_fresh_spec())
    r.storage_uri, r.preview_uri = storage.put(r.render_id, full, prev)
    metadata.insert(r)

    if metadata._is_sqlite():
        p = metadata._sqlite_path()
        con = sqlite3.connect(p)
        row = con.execute(
            "SELECT formula_id, checksum FROM render_events WHERE render_id=?",
            (r.render_id,),
        ).fetchone()
    else:
        import psycopg

        with psycopg.connect(metadata.settings.postgres_dsn) as c:
            row = c.execute(
                "SELECT formula_id, checksum FROM render_events WHERE render_id=%s",
                (r.render_id,),
            ).fetchone()

    assert row is not None
    assert row[0] == "polar_loom"
    assert row[1] == r.checksum


def test_parquet_written():
    metadata.init_db()
    r, full, prev = render(_fresh_spec())
    r.storage_uri, r.preview_uri = storage.put(r.render_id, full, prev)
    metadata.insert(r)
    p = metadata.write_parquet(r)
    assert Path(p).exists()
    assert Path(p).stat().st_size > 0
