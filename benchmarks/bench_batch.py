"""
Batch throughput benchmark.

Renders N specs from a fixed grid, writing to SQLite, and reports
throughput (renders/sec) plus per-stage cost (render, storage, metadata).

Usage:
    python -m benchmarks.bench_batch --n 200
"""
from __future__ import annotations

import argparse
import os
import tempfile
import time
from pathlib import Path

from benchmarks.common import print_result, save, summarize

FORMULAS = [
    ("polar_loom",    {"rings": 8,  "twist": 1.5, "decay": 2.2, "fold": 1.0}),
    ("harmonic_grid", {"nx": 5, "ny": 3, "phase": 0.0, "skew": 0.0, "mix": 0.5}),
    ("moire_grid",    {"f1": 12.0, "f2": 12.4, "angle": 0.05, "mix": 0.5, "sharpen": 1.3}),
]


def _setup_env(tmp: Path) -> None:
    os.environ["POSTGRES_DSN"]  = f"sqlite:///{tmp / 'bench.sqlite'}"
    os.environ["USE_S3"]        = "false"
    os.environ["ARTIFACT_ROOT"] = str(tmp / "renders")
    os.environ["PARQUET_ROOT"]  = str(tmp / "parquet")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200, help="Number of renders")
    ap.add_argument("--width", type=int, default=400)
    ap.add_argument("--height", type=int, default=300)
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="mrp_batch_"))
    _setup_env(tmp)

    from mrp import metadata, storage
    from mrp.models import RenderSpec
    from mrp.renderer import render

    metadata.init_db()

    runtimes: list[int] = []
    bytes_full_total = 0
    t_start = time.perf_counter()

    for i in range(args.n):
        fid, params = FORMULAS[i % len(FORMULAS)]
        spec = RenderSpec(formula_id=fid, width=args.width,
                          height=args.height, params=params)
        r, full, prev = render(spec)
        r.storage_uri, r.preview_uri = storage.put(r.render_id, full, prev)
        metadata.insert(r)
        metadata.write_parquet(r)
        runtimes.append(r.runtime_ms)
        bytes_full_total += r.bytes_full

    wall = time.perf_counter() - t_start
    throughput = args.n / wall

    payload = {
        "benchmark": "batch",
        "n": args.n,
        "width": args.width,
        "height": args.height,
        "wall_seconds": round(wall, 3),
        "throughput_rps": round(throughput, 2),
        "mb_written": round(bytes_full_total / 1e6, 3),
        "mb_per_second": round(bytes_full_total / 1e6 / wall, 3),
        "render_stats": summarize(runtimes),
        "formulas": [f[0] for f in FORMULAS],
    }
    save("batch", payload)
    print_result("batch", payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
