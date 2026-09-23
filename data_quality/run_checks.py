"""Lightweight data-quality checks against render_events."""
from __future__ import annotations
import os, re, sqlite3, sys

_DSN = os.environ.get("POSTGRES_DSN", "sqlite:///./data/mrp.sqlite")
_HEX64 = re.compile(r"^[a-f0-9]{64}$")

def _rows(dsn: str):
    if dsn.startswith("sqlite://"):
        p = dsn.replace("sqlite:///", "", 1) if dsn.startswith("sqlite:///") else dsn.replace("sqlite://", "", 1)
        con = sqlite3.connect(p)
        return con.execute("""
            SELECT render_id, formula_hash, checksum, width, height,
                   runtime_ms, bytes_full, bytes_preview
            FROM render_events
        """).fetchall()
    import psycopg
    with psycopg.connect(dsn) as c:
        return c.execute("""
            SELECT render_id, formula_hash, checksum, width, height,
                   runtime_ms, bytes_full, bytes_preview
            FROM render_events
        """).fetchall()

def check() -> int:
    rows = _rows(_DSN)
    failures: list[str] = []
    if not rows:
        failures.append("table has zero rows")
    seen = set()
    for (rid, fhash, chk, w, h, ms, bfull, bprev) in rows:
        if rid in seen: failures.append(f"duplicate render_id: {rid}")
        seen.add(rid)
        if not _HEX64.match(fhash or ""): failures.append(f"formula_hash not sha256-hex: {rid}")
        if not _HEX64.match(chk or ""):   failures.append(f"checksum not sha256-hex: {rid}")
        if ms is None or ms < 1:          failures.append(f"runtime_ms < 1: {rid}")
        if not (32 <= (w or 0) <= 16384): failures.append(f"width out of range: {rid}")
        if not (32 <= (h or 0) <= 16384): failures.append(f"height out of range: {rid}")
        if bfull is None or bfull < 1024: failures.append(f"bytes_full < 1024: {rid}")
        if bprev is not None and bfull is not None and bprev > bfull:
            failures.append(f"preview larger than full: {rid}")
    print(f"rows checked: {len(rows)}")
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures: print(f"  - {f}")
        return 1
    print("ALL CHECKS PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(check())
