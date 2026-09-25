"""
Backfill benchmark: simulate 30 days x 5 specs.

Answers "how long does it take to backfill a month of daily renders?"
without actually invoking Airflow. Useful for capacity planning.

Usage:
    python -m benchmarks.bench_backfill --days 30 --specs-per-day 5
"""
from __future__ import annotations

import argparse
import os
import tempfile
import time
from pathlib import Path

from benchmarks.common import print_result, save, summarize

DAILY_SPECS = [
    ("polar_loom",    {"rings": 12, "twist": 2.0, "decay": 2.2, "fold": 1.0}),
    ("polar_loom",    {"rings": 24, "twist": 3.0, "decay": 2.0, "fold": 1.2}),
    ("harmonic_grid", {"nx": 6, "ny": 4, "phase": 0.1, "skew": 0.0, "mix": 0.5}),
    ("moire_grid",    {"f1": 14.0, "f2": 14.4, "angle": 0.05, "mix": 0.5, "sharpen": 1.4}),
    ("moire_grid",    {"f1": 22.0, "f2": 22.6, "angle": 0.06, "mix": 0.5, "sharpen": 1.6}),
]


def _setup_env(tmp: Path) -> None:
    os.environ["POSTGRES_DSN"]  = f"sqlite:///{tmp / 'bench.sqlite'}"
    os.environ["USE_S3"]        = "false"
    os.environ["ARTIFACT_ROOT"] = str(tmp / "renders")
    os.environ["PARQUET_ROOT"]  = str(tmp / "parquet")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--specs-per-day", type=int, default=5)
    ap.add_argument("--width", type=int, default=400)
    ap.add_argument("--height", type=int, default=300)
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="mrp_backfill_"))
    _setup_env(tmp)

    from mrp import metadata, storage
    from mrp.models import RenderSpec
    from mrp.renderer import render

    metadata.init_db()

    total = args.days * args.specs_per_day
    runtimes: list[int] = []
    per_day_seconds: list[float] = []
    bytes_total = 0

    t_start = time.perf_counter()
    for _day in range(args.days):
        t_day = time.perf_counter()
        for i in range(args.specs_per_day):
            fid, params = DAILY_SPECS[i % len(DAILY_SPECS)]
            spec = RenderSpec(formula_id=fid, width=args.width,
                              height=args.height, params=params)
            r, full, prev = render(spec)
            r.storage_uri, r.preview_uri = storage.put(r.render_id, full, prev)
            metadata.insert(r)
            metadata.write_parquet(r)
            runtimes.append(r.runtime_ms)
            bytes_total += r.bytes_full
        per_day_seconds.append(round(time.perf_counter() - t_day, 3))

    wall = time.perf_counter() - t_start

    payload = {
        "benchmark": "backfill",
        "days": args.days,
        "specs_per_day": args.specs_per_day,
        "total_renders": total,
        "width": args.width,
        "height": args.height,
        "wall_seconds": round(wall, 3),
        "seconds_per_day": round(wall / args.days, 3),
        "throughput_rps": round(total / wall, 2),
        "projected_seconds_per_month": round(wall / args.days * 30, 1),
        "per_day_seconds_stats": summarize([int(x * 1000) for x in per_day_seconds]),
        "mb_written": round(bytes_total / 1e6, 3),
        "render_stats": summarize(runtimes),
    }
    save("backfill", payload)
    print_result("backfill", payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
