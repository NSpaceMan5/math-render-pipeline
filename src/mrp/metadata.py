from __future__ import annotations
import json, sqlite3
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from .config import settings
from .models import RenderResult

_DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS render_events (
    render_id     TEXT PRIMARY KEY,
    formula_id    TEXT NOT NULL,
    formula_hash  TEXT NOT NULL,
    params_json   TEXT NOT NULL,
    width         INTEGER NOT NULL,
    height        INTEGER NOT NULL,
    runtime_ms    INTEGER NOT NULL,
    checksum      TEXT NOT NULL,
    storage_uri   TEXT NOT NULL,
    preview_uri   TEXT NOT NULL,
    bytes_full    INTEGER NOT NULL,
    bytes_preview INTEGER NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_render_events_formula ON render_events(formula_id);
CREATE INDEX IF NOT EXISTS ix_render_events_created ON render_events(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_render_events_hash    ON render_events(formula_hash);
"""

_DDL_PG = """
CREATE TABLE IF NOT EXISTS render_events (
    render_id     TEXT PRIMARY KEY,
    formula_id    TEXT NOT NULL,
    formula_hash  TEXT NOT NULL,
    params_json   JSONB NOT NULL,
    width         INT NOT NULL,
    height        INT NOT NULL,
    runtime_ms    INT NOT NULL,
    checksum      TEXT NOT NULL,
    storage_uri   TEXT NOT NULL,
    preview_uri   TEXT NOT NULL,
    bytes_full    BIGINT NOT NULL,
    bytes_preview BIGINT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

def _is_sqlite() -> bool:
    return settings.postgres_dsn.startswith("sqlite://")

def _sqlite_path() -> str:
    s = settings.postgres_dsn
    if s.startswith("sqlite:///"):
        return s[len("sqlite:///"):]
    return s.replace("sqlite://", "", 1)

def init_db() -> None:
    if _is_sqlite():
        p = _sqlite_path()
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(p) as c:
            c.executescript(_DDL_SQLITE)
    else:
        import psycopg
        with psycopg.connect(settings.postgres_dsn, autocommit=True) as c:
            c.execute(_DDL_PG)

def insert(r: RenderResult) -> None:
    row = (r.render_id, r.formula_id, r.formula_hash, json.dumps(r.params_json),
           r.width, r.height, r.runtime_ms, r.checksum,
           r.storage_uri, r.preview_uri, r.bytes_full, r.bytes_preview)
    if _is_sqlite():
        with sqlite3.connect(_sqlite_path()) as c:
            c.execute("""
                INSERT OR IGNORE INTO render_events
                  (render_id, formula_id, formula_hash, params_json, width, height,
                   runtime_ms, checksum, storage_uri, preview_uri,
                   bytes_full, bytes_preview)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, row)
    else:
        import psycopg
        with psycopg.connect(settings.postgres_dsn) as c:
            c.execute("""
                INSERT INTO render_events
                  (render_id, formula_id, formula_hash, params_json, width, height,
                   runtime_ms, checksum, storage_uri, preview_uri,
                   bytes_full, bytes_preview)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (render_id) DO NOTHING
            """, row)
            c.commit()

def write_parquet(r: RenderResult, root: str | None = None) -> Path:
    root = root or settings.parquet_root
    outdir = Path(root) / f"formula_hash={r.formula_hash[:16]}"
    outdir.mkdir(parents=True, exist_ok=True)
    table = pa.table({
        "render_id":     [r.render_id],
        "formula_id":    [r.formula_id],
        "formula_hash":  [r.formula_hash],
        "params_json":   [json.dumps(r.params_json)],
        "width":         [r.width],
        "height":        [r.height],
        "runtime_ms":    [r.runtime_ms],
        "checksum":      [r.checksum],
        "bytes_full":    [r.bytes_full],
        "bytes_preview": [r.bytes_preview],
        "storage_uri":   [r.storage_uri],
    })
    path = outdir / f"{r.render_id}.parquet"
    pq.write_table(table, path, compression="zstd")
    return path
