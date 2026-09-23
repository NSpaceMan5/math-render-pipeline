# Deterministic Mathematical Image Generation Pipeline

[![Tests](https://github.com/WoodinGlass/math-render-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/WoodinGlass/math-render-pipeline/actions/workflows/ci.yml)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://math-render-pipeline-3kvjtr8gsh8rtpxsg4fwtc.streamlit.app/)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A production-grade pipeline that renders mathematical formulas into image
artifacts + structured metadata. Every render is byte-deterministic, fully
traceable, and stored with lineage across filesystem/S3, SQLite/Postgres,
and Parquet.

> Not "math art". A **pipeline** whose payload happens to be math art.

## Live demo

▶️ **[math-render-pipeline.streamlit.app](https://math-render-pipeline-3kvjtr8gsh8rtpxsg4fwtc.streamlit.app/)**

- **Live render** — adjust parameters, see output instantly
- **Gallery** — seeded renders from all three formulas
- **Metrics** — runtime, cost per megapixel, raw metadata

## What This Is

A data-engineering pipeline for parameterized image generation. Every render is:

- **Deterministic** — same spec ⇒ byte-identical PNG. No RNG, fixed dtype,
  pure NumPy. `formula_hash = SHA-256(formula_id ‖ params ‖ w ‖ h ‖ samples)`.
- **Reproducible** — `checksum = SHA-256(PNG bytes)`. Any drift in output
  bytes is detected automatically.
- **Traceable** — every artifact carries its formula, params, and version.
  Lineage is queryable via SQL and Parquet.
- **Portable** — SQLite or Postgres metadata; filesystem or S3/MinIO
  artifacts. Same code, two backends, chosen by env var.
- **Dual-path ingestion** — batch CLI inserts directly; streaming path
  publishes to Kafka and a consumer group writes idempotently.
- **Columnar-friendly** — metadata is small and structured; images are large
  and unstructured. They are stored and queried separately.
- **Tested** — pytest suite covering shape, dtype, determinism, checksum,
  parameter sensitivity, and streaming idempotency.

## Available Formulas

| ID              | Family                                | Params                                | Output       |
|-----------------|---------------------------------------|---------------------------------------|--------------|
| `polar_loom`    | Polar harmonics with radial shear     | `rings, twist, decay, fold`           | PNG (H,W,3)  |
| `harmonic_grid` | Cartesian orthogonal harmonics        | `nx, ny, phase, skew, mix`            | PNG (H,W,3)  |
| `moire_grid`    | Interference between rotated lattices | `f1, f2, angle, mix, sharpen`         | PNG (H,W,3)  |

**Legend:**
- *RGB* = 8-bit unsigned, shape `(H, W, 3)`
- *Params* = keyword arguments passed to the evaluator
- New formulas register in `src/mrp/evaluators/registry.py`

## Quick Start

### Single render

```bash
pip install -e .
mrp run --formula polar_loom --width 1600 --height 1200 \
  --params '{"rings":28,"twist":2.7,"decay":2.1,"fold":1.15}'
```

Output:

```json
{
  "render_id": "4b719e1c4b32f914-086e1a27",
  "formula_id": "polar_loom",
  "formula_hash": "4b719e1c4b32f91400fddb163b6b24c6830742630e2f74a9f77d1049ae1b8d87",
  "params_json": {"rings": 28, "twist": 2.7, "decay": 2.1, "fold": 1.15},
  "width": 1600, "height": 1200,
  "runtime_ms": 10702,
  "checksum": "c73c1002d72460e321e6688ea9ae40bc104e4f082b1aeb33960e4c5a21503c43",
  "storage_uri": "file:///.../full.png",
  "preview_uri": "file:///.../preview.png",
  "bytes_full": 408395,
  "bytes_preview": 84190
}
```

### Batch render

```bash
mrp batch --csv params/example_params.csv
```

CSV columns: `formula_id, width, height, params_json`.

### Inspect the registry

```bash
mrp formulas
```

## Metadata Schema

Table `render_events` (SQLite or Postgres):

| Column          | Type        | Meaning                                  |
|-----------------|-------------|------------------------------------------|
| `render_id`     | TEXT PK     | `formula_hash[:16]` + short uuid         |
| `formula_id`    | TEXT        | e.g. `polar_loom`                        |
| `formula_hash`  | TEXT        | SHA-256 of spec                          |
| `params_json`   | JSON/TEXT   | Formula parameters                       |
| `width`, `height` | INT       | Output dimensions                        |
| `runtime_ms`    | INT         | Wall-clock render time                   |
| `checksum`      | TEXT        | SHA-256 of PNG bytes                     |
| `storage_uri`   | TEXT        | `file://` or `s3://` to full render      |
| `preview_uri`   | TEXT        | `file://` or `s3://` to 512px preview    |
| `bytes_full`    | BIGINT      | Size of full PNG                         |
| `bytes_preview` | BIGINT      | Size of preview PNG                      |
| `ingest_source` | TEXT        | `batch` or `stream`                      |
| `created_at`    | TIMESTAMPTZ | Insert time                              |

Parquet mirror is partitioned by `formula_hash[:16]` and written with ZSTD.

## Determinism Contract

| Artifact       | How                                                          |
|----------------|--------------------------------------------------------------|
| PNG bytes      | NumPy → Pillow, no RNG, fixed dtype, stable compressor       |
| `formula_hash` | SHA-256 of `(formula_id, params, width, height, samples)`    |
| `checksum`     | SHA-256 of the PNG payload                                   |
| `render_id`    | `formula_hash[:16]` + `uuid4()[:8]` (collision-free inserts) |

Implication: the same spec always produces the same bytes; different runs
produce distinct `render_id`s so every render is preserved as an event.

## Architecture

```
                       ┌──▶ PNG full + preview ──▶ filesystem / S3
                       │
params.csv ──▶ Renderer ──▶ SQLite / Postgres: render_events
                       │
                       ├──▶ Parquet: partitioned by formula_hash[:16]
                       │
                       └──▶ Kafka topic: render.events
                                  │
                                  ▼
                           Consumer (group: mrp-consumer)
                                  │
                                  ▼
                           Postgres (idempotent on render_id)
```

Layers:

- **Evaluator** — pure NumPy. No IO. Deterministic by construction.
- **Renderer** — wraps evaluator, produces bytes, computes checksum.
- **Storage** — filesystem or S3/MinIO, selected by `USE_S3`.
- **Metadata** — SQLite or Postgres, selected by `POSTGRES_DSN` scheme.
- **Producer** — publishes to Kafka/Redpanda on `mrp produce`.
- **Consumer** — reads `render.events`, writes idempotently.
- **CLI** — `mrp run`, `mrp batch`, `mrp formulas`, `mrp produce`, `mrp consume`.

## Streaming

Two ingestion paths converge on `render_events`:

| Path    | Command                            | Backend                    |
|---------|------------------------------------|----------------------------|
| Batch   | `mrp run` / `mrp batch`            | direct insert              |
| Stream  | `mrp produce` → Kafka → consumer   | Redpanda + consumer group  |

```bash
# Start the streaming stack
docker compose up -d redpanda postgres consumer

# Publish renders to render.events
mrp produce --csv params/example_params.csv

# Consumer is idempotent on render_id — safe against re-delivery
mrp consume --max-messages 5
```

The `ingest_source` column ('batch' | 'stream') distinguishes the two
paths; Grafana tracks them separately.

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# edit .env if you want Postgres or S3
```

Minimal (no Postgres, no S3, no Kafka):

```
POSTGRES_DSN=sqlite:///./data/mrp.sqlite
USE_S3=false
```

With streaming:

```bash
pip install -e ".[dev,streaming]"
```

## Testing

```bash
pytest -q
```

Coverage:

- `test_evaluators.py` — output shape/dtype, determinism, param sensitivity.
- `test_harmonic_grid.py`, `test_moire_grid.py` — per-formula correctness.
- `test_registry.py` — plural registry, unknown-name error handling.
- `test_renderer.py` — hash stability, checksum format, preview < full.
- `test_metadata.py` — insert, idempotency, Parquet write.
- `test_streaming_schemas.py` — event round-trip through Pydantic.
- `test_streaming_metadata.py` — consumer insert + dedup + migration.

## CI

GitHub Actions runs on every push and PR:

1. `pip install -e ".[dev]"`
2. `ruff check src tests`
3. `pytest -q`
4. Smoke render at 320×240

## Visual Output

### `polar_loom` — default parameters

![polar_loom default](docs/preview/polar_loom_default.png)

Default: `rings=28, twist=2.7, decay=2.1, fold=1.15`, rendered at 1600×1200.
Polar-harmonic interference with radial shearing.

### `polar_loom` — parameter sweep

![polar_loom sweep](docs/preview/polar_loom_sweep.png)

Four rows, four values each — same code, only one parameter changed per
panel. Top to bottom: `rings`, `twist`, `decay`, `fold`.

### `moire_grid` — parameter sweep

![moire_grid sweep](docs/preview/moire_grid_sweep.png)

Interference between two rotated grids. Rows: `f2` (22.0 → 23.0);
columns: `angle` (0.02 → 0.25 rad). Beat fringe width grows as the two
frequencies converge and the rotation angle decreases.

## Trade-offs

See [`docs/blog/reproducible-math-art.md`](docs/blog/reproducible-math-art.md)
for a longer discussion. Summary:

- **Determinism** buys idempotency, auditability, cheap diffs.
- **Cost:** `O(pixels × rings × 3)` per image. Does not scale like
  neural rendering; scales like a scientific compute job.
- **Right tool when:** reproducibility is a hard requirement, sweeps
  matter, artifacts must be diffable.
- **Wrong tool when:** photorealism or interactive latency is required.

## Roadmap

- [x] Second and third formulas (`harmonic_grid`, `moire_grid`)
- [x] Airflow DAG (`dags/render_pipeline_dag.py`)
- [x] dbt models: `stg_renders → fct_render_events → agg_cost_daily`
- [x] Grafana dashboard: CPU-minutes/day, renders/day, storage MB
- [x] Streaming layer (Kafka/Redpanda producer + consumer)
- [x] Live demo on Streamlit Cloud
- [ ] Great Expectations runtime checks against `render_events`
- [ ] Terraform: S3 bucket with lifecycle tiering + RDS Postgres
- [ ] Real SAR/thermal rendering as a fourth formula family

## License

MIT — see [LICENSE].
