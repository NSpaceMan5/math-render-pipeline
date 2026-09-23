# Deterministic Mathematical Image Generation Pipeline

Turn parameterized mathematical formulas into image artifacts + structured
metadata. Every render is byte-deterministic and fully traceable.

> Not "math art". A **pipeline** whose payload happens to be math art.

## Pipeline

```
params.csv ──▶ Renderer (NumPy) ──▶ PNG full + preview (filesystem/S3)
                        │
                        ├──▶ SQLite/Postgres: render_events
                        └──▶ Parquet: partitioned by formula_hash
```

## Usage

```bash
pip install -e .
mrp formulas
mrp run --formula polar_loom --width 1600 --height 1200 \
  --params '{"rings":28,"twist":2.7,"decay":2.1,"fold":1.15}'
mrp batch --csv params/example_params.csv
pytest -q
```

## Determinism contract

| Artifact       | How                                                         |
|----------------|-------------------------------------------------------------|
| PNG bytes      | NumPy → Pillow, no RNG, fixed dtype                         |
| `formula_hash` | SHA-256 of `(formula_id, params, width, height, samples)`   |
| `checksum`     | SHA-256 of the PNG payload                                  |
| `render_id`    | `formula_hash[:16]` + short uuid                            |

## Formula: `polar_loom`

Original polar-harmonic formulation. See
`src/mrp/evaluators/polar_loom.py`.

## Metadata schema

See `src/mrp/metadata.py` (`render_events` table).

## License

MIT
```
