from __future__ import annotations
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

from mrp.evaluators.polar_loom import polar_loom, DEFAULTS as PL_DEFAULTS
from mrp.evaluators.harmonic_grid import harmonic_grid, DEFAULTS as HG_DEFAULTS
from mrp.evaluators.moire_grid import moire_grid, DEFAULTS as MG_DEFAULTS


st.set_page_config(
    page_title="Math Render Pipeline",
    page_icon="🧮",
    layout="wide",
)

DEMO = ROOT / "demo_data"
THUMBS = DEMO / "thumbs"
PARQUET = DEMO / "renders.parquet"

FORMULAS = {
    "polar_loom":    (polar_loom,    PL_DEFAULTS, "Polar harmonic interference"),
    "harmonic_grid": (harmonic_grid, HG_DEFAULTS, "Cartesian orthogonal harmonics"),
    "moire_grid":    (moire_grid,    MG_DEFAULTS, "Interference of two rotated grids"),
}

st.title("Deterministic Mathematical Image Generation Pipeline")
st.caption(
    "NumPy renderer · byte-deterministic output · "
    "metadata in Parquet · two formulas"
)

tab_live, tab_gallery, tab_metrics, tab_about = st.tabs(
    ["🎨 Live render", "🖼 Gallery", "📊 Metrics", "ℹ️ About"]
)


@st.cache_data(show_spinner=False)
def _load_parquet(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


with tab_live:
    col_left, col_right = st.columns([1, 2], gap="large")

    with col_left:
        formula_id = st.selectbox("Formula", list(FORMULAS.keys()))
        fn, defaults, desc = FORMULAS[formula_id]
        st.caption(desc)

        params: dict = {}
        for k, v in defaults.items():
            if isinstance(v, int):
                params[k] = st.slider(k, 1, max(v * 3, 20), v)
            else:
                params[k] = st.slider(
                    k, 0.0, max(v * 3, 5.0), float(v), step=0.05
                )

        width  = st.slider("width",  256, 1200, 640, step=32)
        height = st.slider("height", 256, 900, 480, step=32)

        st.code(json.dumps(params, indent=2), language="json")

    with col_right:
        arr = fn(width, height, **params)
        st.image(arr, caption=f"{formula_id} · {width}×{height}",
                 use_container_width=True)

with tab_gallery:
    if PARQUET.exists():
        df = _load_parquet(str(PARQUET))
        st.write(f"**{len(df)}** renders across **{df['formula_id'].nunique()}** formulas")
        cols = st.columns(4)
        for i, row in df.iterrows():
            with cols[i % 4]:
                thumb = THUMBS / f"{row['render_id']}.png"
                if thumb.exists():
                    st.image(str(thumb))
                st.caption(
                    f"`{row['formula_id']}` · {row['width']}×{row['height']} · "
                    f"{row['runtime_ms']} ms"
                )
    else:
        st.info("No demo data. Run `python scripts/build_demo_data.py`.")

with tab_metrics:
    if PARQUET.exists():
        df = _load_parquet(str(PARQUET))
        df["mp"]        = df["width"] * df["height"] / 1e6
        df["us_per_mp"] = df["runtime_ms"] / df["mp"] / 1000  # ms → µs

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total renders", len(df))
        c2.metric("Formulas",      df["formula_id"].nunique())
        c3.metric("Total MB",      round(df["bytes_full"].sum() / 1024 / 1024, 2))
        c4.metric("Avg runtime",   f"{df['runtime_ms'].mean():.0f} ms")

        st.subheader("Average runtime by formula (ms)")
        st.bar_chart(df.groupby("formula_id")["runtime_ms"].mean())

        st.subheader("Cost per megapixel (µs/MP)")
        st.bar_chart(df.groupby("formula_id")["us_per_mp"].mean())

        st.subheader("Raw metadata")
        st.dataframe(
            df[[
                "formula_id", "width", "height",
                "runtime_ms", "bytes_full", "checksum",
            ]].head(20),
            use_container_width=True,
        )
    else:
        st.info("No demo data.")

with tab_about:
    st.markdown("""
### What this is

A deterministic pipeline that renders mathematical formulas into image
artifacts and structured metadata.

- **Determinism** — same `(formula_id, params, w, h)` ⇒ byte-identical PNG.
  `formula_hash = sha256(spec)`, `checksum = sha256(png_bytes)`.
- **Three formulas** — `polar_loom` (polar harmonics with radial shear),
  `harmonic_grid` (Cartesian orthogonal harmonics), `moire_grid`
  (interference between two rotated lattices).
- **Metadata** — Parquet mirror partitioned by `formula_hash`, plus
  SQLite/Postgres `render_events` for the batch path.
- **Streaming** — optional Kafka/Redpanda producer + consumer
  (`mrp produce` / `mrp consume`), idempotent on `render_id`.
- **Orchestration** — Airflow DAG, dbt models, Grafana dashboard.

Source: [github.com/NSpaceMan5/math-render-pipeline](https://github.com/NSpaceMan5/math-render-pipeline)
""")
