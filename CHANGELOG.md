# Changelog

Follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
