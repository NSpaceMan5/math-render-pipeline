"""Shared helpers for benchmarks."""
from __future__ import annotations

import json
import statistics
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "benchmarks" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


@contextmanager
def timer():
    """Yield a callable that returns elapsed seconds."""
    t0 = time.perf_counter()
    box: dict[str, float] = {}
    def elapsed() -> float:
        box["elapsed"] = time.perf_counter() - t0
        return box["elapsed"]
    yield elapsed


def percentile(values: list[float], q: float) -> float:
    """Simple percentile (linear interpolation)."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    idx = (len(s) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(s) - 1)
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def summarize(runtimes_ms: list[int]) -> dict[str, float]:
    if not runtimes_ms:
        return {"count": 0}
    return {
        "count": len(runtimes_ms),
        "sum_ms": sum(runtimes_ms),
        "mean_ms": round(statistics.fmean(runtimes_ms), 3),
        "p50_ms": round(percentile(runtimes_ms, 0.50), 3),
        "p95_ms": round(percentile(runtimes_ms, 0.95), 3),
        "p99_ms": round(percentile(runtimes_ms, 0.99), 3),
        "min_ms": min(runtimes_ms),
        "max_ms": max(runtimes_ms),
    }


def save(name: str, payload: dict[str, Any]) -> Path:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    path = RESULTS / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2))
    return path


def print_result(name: str, payload: dict[str, Any]) -> None:
    print(f"\n=== {name} ===")
    for k, v in payload.items():
        if k == "generated_at":
            continue
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")
