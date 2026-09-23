# Deterministic Mathematical Image Generation Pipeline

![Tests](https://github.com/NSpaceMan5/math-render-pipeline/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![NumPy](https://img.shields.io/badge/numpy-1.26+-013243)
![License](https://img.shields.io/badge/license-MIT-green)

A production-grade pipeline that renders mathematical formulas into image
artifacts + structured metadata. Every render is byte-deterministic, fully
traceable, and stored with lineage across filesystem/S3, SQLite/Postgres,
and Parquet.

> Not "math art". A **pipeline** whose payload happens to be math art.

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
- **Columnar-friendly** — metadata is small and structured; images are large
  and unstructured. They are stored and queried separately.
- **Tested** — pytest suite covering shape, dtype, determinism, checksum,
  and parameter sensitivity.

## Available Formulas

| ID             | Channels | Params                        | Output        |
|----------------|----------|-------------------------------|---------------|
| `polar_loom`   | RGB      | `rings, twist, decay, fold`   | PNG (H,W,3)   |

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
params.csv ──▶ Renderer (NumPy) ──▶ PNG full + preview ──▶ filesystem / S3
                     │
                     ├──▶ SQLite / Postgres: render_events
                     └──▶ Parquet: partitioned by formula_hash[:16]
```

Layers:

- **Evaluator** — pure NumPy. No IO. Deterministic by construction.
- **Renderer** — wraps evaluator, produces bytes, computes checksum.
- **Storage** — filesystem or S3/MinIO, selected by `USE_S3`.
- **Metadata** — SQLite or Postgres, selected by `POSTGRES_DSN` scheme.
- **CLI** — `mrp run`, `mrp batch`, `mrp formulas`.

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# edit .env if you want Postgres or S3
```

Minimal (no Postgres, no S3):

```
POSTGRES_DSN=sqlite:///./data/mrp.sqlite
USE_S3=false
```

## Testing

```bash
pytest -q
```

Coverage:

- `test_evaluators.py` — output shape/dtype, determinism, param sensitivity,
  non-blank check.
- `test_renderer.py` — hash stability, checksum format, preview < full.

## CI

GitHub Actions runs on every push and PR:

1. `pip install -e ".[dev]"`
2. `ruff check src tests`
3. `pytest -q`
4. Smoke render at 320×240

## Visual Output

_Add preview PNGs to `docs/preview/` and reference them here. Only
`docs/preview/*.png` is whitelisted in `.gitignore`; all other PNGs are
excluded from the repo._

```markdown
![polar_loom default](docs/preview/polar_loom_default.png)
```

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

- [ ] Second formula (`harmonic_grid`) to prove registry pluralism
- [ ] Great Expectations runtime checks against `render_events`
- [ ] dbt models: `stg_renders → fct_render_events → agg_cost_daily`
- [ ] Airflow DAG (`dags/render_pipeline_dag.py`)
- [ ] Grafana dashboard: CPU-minutes/day, renders/day, storage MB
- [ ] Terraform: S3 bucket with lifecycle tiering + RDS Postgres

## License

MIT — see [LICENSE].
```
