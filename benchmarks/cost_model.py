"""
Cost model: USD per 1000 renders.

Reads benchmark results (benchmarks/results/*.json) and applies AWS prices
to estimate cost per 1000 renders for two scenarios:

  * on-demand, always-on
  * spot + S3 lifecycle tiering

Prices are hardcoded constants from AWS us-east-1 (2026) — update the
PRICES dict to reflect current rates or a different region.

Usage:
    python -m benchmarks.cost_model
    python -m benchmarks.cost_model --json
"""
from __future__ import annotations

import argparse
import json

from benchmarks.common import RESULTS, print_result, save

# ---------------------------------------------------------------- prices
# All prices in USD, us-east-1, September 2026 (round numbers, adjust as
# rates change).
PRICES = {
    "compute": {
        "c6i.large_ondemand_per_hour": 0.085,
        "c6i.large_spot_per_hour":     0.025,   # ~70% discount typical
    },
    "storage_s3_per_gb_month": {
        "standard": 0.023,
        "standard_ia": 0.0125,
        "glacier_ir": 0.004,
    },
    "storage_requests_per_1k": {
        "put": 0.005,
        "get": 0.0004,
    },
    "rds": {
        "db.t4g.micro_per_hour": 0.016,
    },
    "cloudwatch_logs_per_gb": 0.50,
}

DEFAULT_BENCH = "batch"


# ---------------------------------------------------------------- helpers
def _load(name: str) -> dict:
    path = RESULTS / f"{name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def compute_cost(renders: int, mean_runtime_ms: float,
                 bytes_per_render: int,
                 spot: bool) -> dict:
    """Compute cost for a given workload size."""
    # 1) compute time
    total_cpu_seconds = renders * (mean_runtime_ms / 1000.0)
    total_cpu_hours = total_cpu_seconds / 3600.0
    rate = (PRICES["compute"]["c6i.large_spot_per_hour"] if spot
            else PRICES["compute"]["c6i.large_ondemand_per_hour"])
    compute_usd = total_cpu_hours * rate

    # 2) storage (assume kept 1 month)
    total_bytes = renders * bytes_per_render
    total_gb = total_bytes / 1e9
    storage_class = "glacier_ir" if spot else "standard"
    storage_usd = total_gb * PRICES["storage_s3_per_gb_month"][storage_class]

    # 3) S3 PUT requests (1 per render)
    put_usd = (renders / 1000.0) * PRICES["storage_requests_per_1k"]["put"]

    # 4) RDS — amortized. Assume pipeline finishes in 1 hour, db idle.
    rds_usd = PRICES["rds"]["db.t4g.micro_per_hour"]

    # 5) Logs — assume ~2 KB per render (JSON)
    logs_gb = (renders * 2 * 1024) / 1e9
    logs_usd = logs_gb * PRICES["cloudwatch_logs_per_gb"]

    total = compute_usd + storage_usd + put_usd + rds_usd + logs_usd
    return {
        "renders": renders,
        "compute_usd": round(compute_usd, 4),
        "storage_usd": round(storage_usd, 4),
        "put_requests_usd": round(put_usd, 4),
        "rds_usd": round(rds_usd, 4),
        "logs_usd": round(logs_usd, 4),
        "total_usd": round(total, 4),
        "usd_per_1000_renders": round(total / renders * 1000, 3),
        "total_cpu_hours": round(total_cpu_hours, 4),
        "total_gb": round(total_gb, 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", type=int, default=1000)
    ap.add_argument("--bench", default=DEFAULT_BENCH,
                    help="benchmark name to read timings from")
    ap.add_argument("--json", action="store_true",
                    help="Print raw JSON instead of formatted report")
    args = ap.parse_args()

    bench = _load(args.bench)
    if not bench:
        # fall back to hardcoded defaults
        mean_ms = 30.0
        bytes_per = 400_000
        source = "fallback"
    else:
        mean_ms = bench.get("render_stats", {}).get("mean_ms", 30.0)
        # bytes per render — derived from mb_written / n if not present
        n = bench.get("n", 1) or 1
        mb = bench.get("mb_written", 0.4)
        bytes_per = int(mb * 1e6 / n)
        source = args.bench

    on_demand = compute_cost(args.renders, mean_ms, bytes_per, spot=False)
    spot      = compute_cost(args.renders, mean_ms, bytes_per, spot=True)

    payload = {
        "benchmark": "cost_model",
        "source_benchmark": source,
        "renders": args.renders,
        "inputs": {
            "mean_runtime_ms": round(mean_ms, 3),
            "bytes_per_render": bytes_per,
        },
        "on_demand": on_demand,
        "spot": spot,
        "savings_pct_spot_vs_ondemand": round(
            (1 - spot["total_usd"] / on_demand["total_usd"]) * 100, 1
        ) if on_demand["total_usd"] > 0 else 0,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print_result("cost_model", payload)

    save("cost_model", payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
