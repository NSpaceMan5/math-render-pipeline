"""
Scale test: run N renders and profile where time is spent.

Breaks down the pipeline into stages (render, storage write, metadata insert,
parquet write) so we can identify the bottleneck.

Usage:
    python -m benchmarks.bench_scale --n 10000 --width 128 --height 128
"""
from __future__ import annotations

import argparse
import os
import tempfile
import time
from pathlib import Path

from benchmarks.common import print_result, save, summarize

FORMULAS = [
    ("polar_loom",    {"rings": 6}),
    ("harmonic_grid", {"nx": 4, "ny": 3}),
    ("moire_grid",    {"f1": 10.0, "f2": 10.4}),
]


def _setup_env(tmp: Path) -> None:
    os.environ["POSTGRES_DSN"]  = f"sqlite:///{tmp / 'bench.sqlite'}"
    os.environ["USE_S3"]        = "false"
    os.environ["ARTIFACT_ROOT"] = str(tmp / "renders")
    os.environ["PARQUET_ROOT"]  = str(tmp / "parquet")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--width", type=int, default=128)
    ap.add_argument("--height", type=int, default=128)
    ap.add_argument("--no-parquet", action="store_true",
                    help="Skip parquet write to isolate its cost")
    ap.add_argument("--no-storage", action="store_true",
                    help="Skip storage write to isolate its cost")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="mrp_scale_"))
    _setup_env(tmp)

    from mrp import metadata, storage
    from mrp.models import RenderSpec
    from mrp.renderer import render

    metadata.init_db()

    t_render = 0.0
    t_storage = 0.0
    t_meta = 0.0
    t_parquet = 0.0
    runtimes: list[int] = []
    bytes_total = 0

    t_start = time.perf_counter()
    for i in range(args.n):
        fid, params = FORMULAS[i % len(FORMULAS)]
        spec = RenderSpec(formula_id=fid, width=args.width,
                          height=args.height, params=params)

        t0 = time.perf_counter()
        r, full, prev = render(spec)
        t_render += time.perf_counter() - t0

        if not args.no_storage:
            t0 = time.perf_counter()
            r.storage_uri, r.preview_uri = storage.put(r.render_id, full, prev)
            t_storage += time.perf_counter() - t0

        t0 = time.perf_counter()
        metadata.insert(r)
        t_meta += time.perf_counter() - t0

        if not args.no_parquet:
            t0 = time.perf_counter()
            metadata.write_parquet(r)
            t_parquet += time.perf_counter() - t0

        runtimes.append(r.runtime_ms)
        bytes_total += r.bytes_full

    wall = time.perf_counter() - t_start
    stages = {
        "render":  round(t_render, 3),
        "storage": round(t_storage, 3),
        "metadata": round(t_meta, 3),
        "parquet": round(t_parquet, 3),
    }
    bottleneck = max(stages.items(), key=lambda kv: kv[1])[0]

    payload = {
        "benchmark": "scale",
        "n": args.n,
        "width": args.width,
        "height": args.height,
        "wall_seconds": round(wall, 3),
        "throughput_rps": round(args.n / wall, 2),
        "stages_seconds": stages,
        "stage_pct": {k: round(v / wall * 100, 1) for k, v in stages.items()},
        "bottleneck": bottleneck,
        "mb_written": round(bytes_total / 1e6, 3),
        "render_stats": summarize(runtimes),
        "skipped_storage": args.no_storage,
        "skipped_parquet": args.no_parquet,
    }
    save("scale", payload)
    print_result("scale", payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
