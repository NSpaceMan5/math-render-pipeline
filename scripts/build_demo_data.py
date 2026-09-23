"""
Build small demo data for the Streamlit app.

Renders 8 fixed specs, saves 256px thumbnails + Parquet metadata.
Total output stays well under 2 MB so it can be committed to the repo.

Run:
    python scripts/build_demo_data.py
"""
from __future__ import annotations
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image
import pandas as pd

from mrp.models import RenderSpec
from mrp.renderer import render

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo_data"
THUMBS = DEMO / "thumbs"
DEMO.mkdir(exist_ok=True)
THUMBS.mkdir(exist_ok=True)

SEEDS = [
    ("polar_loom",    {"rings": 8,  "twist": 1.0, "decay": 2.5, "fold": 1.0},      640, 480),
    ("polar_loom",    {"rings": 16, "twist": 1.8, "decay": 2.4, "fold": 1.0},      640, 480),
    ("polar_loom",    {"rings": 28, "twist": 2.7, "decay": 2.1, "fold": 1.15},     640, 480),
    ("polar_loom",    {"rings": 48, "twist": 3.6, "decay": 1.8, "fold": 1.3},      640, 480),
    ("harmonic_grid", {"nx": 6,  "ny": 4,  "phase": 0.0, "skew": 0.0, "mix": 0.5}, 640, 480),
    ("harmonic_grid", {"nx": 10, "ny": 6,  "phase": 0.3, "skew": 0.0, "mix": 0.7}, 640, 480),
    ("harmonic_grid", {"nx": 14, "ny": 8,  "phase": 0.6, "skew": 0.4, "mix": 0.3}, 640, 480),
    ("harmonic_grid", {"nx": 6,  "ny": 12, "phase": 0.9, "skew": 0.8, "mix": 0.9}, 640, 480),
]


def main():
    rows = []
    for i, (fid, params, w, h) in enumerate(SEEDS, 1):
        spec = RenderSpec(formula_id=fid, width=w, height=h, params=params)
        r, full, prev = render(spec)

        img = Image.open(io.BytesIO(full)).convert("RGB")
        img.thumbnail((256, 256))
        img.save(THUMBS / f"{r.render_id}.png", optimize=True, compress_level=9)

        rows.append({
            "render_id":     r.render_id,
            "formula_id":    r.formula_id,
            "width":         r.width,
            "height":        r.height,
            "runtime_ms":    r.runtime_ms,
            "checksum":      r.checksum,
            "bytes_full":    r.bytes_full,
            "bytes_preview": r.bytes_preview,
        })
        print(f"[{i}/{len(SEEDS)}] {fid:15s} {w}x{h}  {r.runtime_ms:>5d} ms")

    pd.DataFrame(rows).to_parquet(DEMO / "renders.parquet",
                                  compression="zstd", index=False)

    total = sum(f.stat().st_size for f in DEMO.rglob("*") if f.is_file())
    print()
    print(f"wrote {len(rows)} renders to {DEMO}")
    print(f"total size: {total/1024:.1f} KB")


if __name__ == "__main__":
    main()
