.PHONY: up down logs test lint fmt render render-batch dq dq-strict ge migrate stamp integration clean

up:        ; docker compose up -d
down:      ; docker compose down
logs:      ; docker compose logs -f --tail=80
test:      ; pytest -q
lint:      ; ruff check src tests
fmt:       ; ruff format src tests
dq:        ; python data_quality/run_checks.py
dq-strict: ; python data_quality/run_checks.py --strict-integrity
ge:        ; python data_quality/run_ge.py
migrate:   ; alembic upgrade head
stamp:     ; alembic stamp head
integration: ; pytest -q -m integration tests/integration -v
metrics:   ; curl -s localhost:9100/metrics | grep mrp_
clean:     ; rm -rf data/ dbt/target dbt/logs .pytest_cache .ruff_cache

render:
	mrp run --formula polar_loom --width 1600 --height 1200 \
	  --params '{"rings":28,"twist":2.7,"decay":2.1,"fold":1.15}'

render-batch:
	mrp batch --csv params/example_params.csv

# ---- spot batch (requires AWS credentials) ----
batch-submit:   ; python scripts/batch_submit.py --job-queue mrp-renderer --job-definition mrp-renderer --spec-file params/example_params.csv
batch-dry:      ; python scripts/batch_submit.py --job-queue mrp-renderer --job-definition mrp-renderer --spec-file params/example_params.csv --dry-run
