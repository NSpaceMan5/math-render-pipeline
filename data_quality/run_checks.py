"""
Data-quality checks against `render_events`.

Tiers:
    schema    — non-null, unique, format, range
    freshness — newest render not older than --max-age-hours
    volume    — at least --min-today renders today
    integrity — Parquet and DB agree on render_id set (best-effort)

Run:
    python data_quality/run_checks.py
    python data_quality/run_checks.py --max-age-hours 6 --min-today 1
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_HEX64 = re.compile(r"^[a-f0-9]{64}$")


def _dsn() -> str:
    return os.environ.get("POSTGRES_DSN", "sqlite:///./data/mrp.sqlite")


def _sqlite_path(dsn: str) -> str:
    if dsn.startswith("sqlite:///"):
        return dsn[len("sqlite:///"):]
    return dsn.replace("sqlite://", "", 1)


def _rows(dsn: str):
    if dsn.startswith("sqlite://"):
        con = sqlite3.connect(_sqlite_path(dsn))
        return con.execute("""
            SELECT render_id, formula_hash, checksum, width, height,
                   runtime_ms, bytes_full, bytes_preview,
                   ingest_source, created_at
            FROM render_events
        """).fetchall()
    import psycopg
    with psycopg.connect(dsn) as c:
        return c.execute("""
            SELECT render_id, formula_hash, checksum, width, height,
                   runtime_ms, bytes_full, bytes_preview,
                   ingest_source, created_at
            FROM render_events
        """).fetchall()


def _parse_ts(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v).replace(" ", "T").replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def check(max_age_hours: float, min_today: int, strict_integrity: bool = False) -> int:
    dsn = _dsn()
    rows = _rows(dsn)
    failures: list[str] = []

    # schema
    if not rows:
        failures.append("table has zero rows")

    seen: set[str] = set()
    for (rid, fhash, chk, w, h, ms, bfull, bprev, src, _ts) in rows:
        if rid in seen:
            failures.append(f"duplicate render_id: {rid}")
        seen.add(rid)
        if not _HEX64.match(fhash or ""):
            failures.append(f"formula_hash not sha256-hex: {rid}")
        if not _HEX64.match(chk or ""):
            failures.append(f"checksum not sha256-hex: {rid}")
        if ms is None or ms < 1:
            failures.append(f"runtime_ms < 1: {rid}")
        if not (32 <= (w or 0) <= 16384):
            failures.append(f"width out of range: {rid}")
        if not (32 <= (h or 0) <= 16384):
            failures.append(f"height out of range: {rid}")
        if bfull is None or bfull < 1024:
            failures.append(f"bytes_full < 1024: {rid}")
        if bprev is not None and bfull is not None and bprev > bfull:
            failures.append(f"preview larger than full: {rid}")
        if src not in ("batch", "stream"):
            failures.append(f"unexpected ingest_source={src!r}: {rid}")

    # freshness
    timestamps = [t for t in (_parse_ts(r[-1]) for r in rows) if t]
    if timestamps:
        newest = max(timestamps)
        age_h = (datetime.now(timezone.utc) - newest).total_seconds() / 3600
        if age_h > max_age_hours:
            failures.append(
                f"stale: newest render is {age_h:.1f}h old (max {max_age_hours}h)"
            )

    # volume
    if min_today > 0 and timestamps:
        today = datetime.now(timezone.utc).date()
        today_count = sum(1 for t in timestamps if t.date() == today)
        if today_count < min_today:
            failures.append(
                f"volume: only {today_count} renders today (min {min_today})"
            )

    # integrity
    # DB is the source of truth; Parquet is an analytics mirror updated
    # by the batch path. Eventual divergence is expected (e.g. a streaming
    # row inserted after the last parquet flush). By default we log it;
    # pass --strict-integrity to turn it into a failure.
    pq_root = Path(os.environ.get("PARQUET_ROOT", "./data/parquet"))
    warnings: list[str] = []
    if pq_root.exists() and rows:
        try:
            import pyarrow.dataset as ds
            dataset = ds.dataset(str(pq_root), format="parquet")
            pq_ids = set(dataset.to_table(columns=["render_id"])
                                 .column("render_id").to_pylist())
            pg_ids = {r[0] for r in rows}
            missing_in_pq = pg_ids - pq_ids
            missing_in_db = pq_ids - pg_ids
            if missing_in_pq:
                msg = (f"{len(missing_in_pq)} render_id(s) in DB not in Parquet")
                (failures if strict_integrity else warnings).append(
                    ("integrity: " if strict_integrity else "integrity warning: ") + msg
                )
            if missing_in_db:
                msg = (f"{len(missing_in_db)} render_id(s) in Parquet not in DB")
                (failures if strict_integrity else warnings).append(
                    ("integrity: " if strict_integrity else "integrity warning: ") + msg
                )
        except Exception as e:
            print(f"(integrity check skipped: {e})")

    print(f"rows checked: {len(rows)}")
    if timestamps:
        print(f"newest:       {max(timestamps).isoformat()}")
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


def _cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-age-hours", type=float, default=24.0)
    ap.add_argument("--min-today", type=int, default=0)
    ap.add_argument("--strict-integrity", action="store_true",
                    help="Treat DB/Parquet divergence as failure")
    a = ap.parse_args()
    sys.exit(check(a.max_age_hours, a.min_today, a.strict_integrity))


if __name__ == "__main__":
    _cli()
