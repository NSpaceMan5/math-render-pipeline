# Changelog

Follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Streaming consumer: retry with exponential backoff, DLQ topic
  (`render.events.dlq`), malformed-JSON poison-pill guard, correlation_id
  in every log line
- Data-quality runtime: freshness, volume, integrity checks
  (`data_quality/run_checks.py`), soft-by-default with `--strict-integrity`
- Property-based tests (Hypothesis) for all three formulas
- DLQ unit tests (`tests/test_consumer_dlq.py`) — no Kafka required
- `KAFKA_DLQ_TOPIC` and `KAFKA_MAX_RETRIES` env vars
- `Makefile` target `dq-strict`

### Added
- Streaming layer: Kafka/Redpanda producer + consumer
- `mrp run --stream`, `mrp produce`, `mrp consume`
- `render_events.ingest_source` column with migration
- Grafana panel 'Stream events per minute'
- Docker Compose: redpanda + console + consumer

### Added
- Second formula: `harmonic_grid`
- Registry plural test, metadata layer tests
- Lightweight data-quality runner
- Airflow DAG, dbt models, Grafana dashboard
- Docker Compose stack (Postgres + MinIO + Grafana + Airflow)
- Makefile, LICENSE, docs, blog post, GitHub templates

## [0.1.0] - 2026-09-23

### Added
- Initial release: `polar_loom`, deterministic renderer, SQLite/Postgres
  metadata, Parquet mirror, CLI, GitHub Actions CI, preview images
