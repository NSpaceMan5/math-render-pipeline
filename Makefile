.PHONY: up down logs test lint fmt render render-batch dq dq-strict clean

up:        ; docker compose up -d
down:      ; docker compose down
logs:      ; docker compose logs -f --tail=80
test:      ; pytest -q
lint:      ; ruff check src tests
fmt:       ; ruff format src tests
dq:        ; python data_quality/run_checks.py
dq-strict: ; python data_quality/run_checks.py --strict-integrity
clean:     ; rm -rf data/ dbt/target dbt/logs .pytest_cache .ruff_cache

render:
	mrp run --formula polar_loom --width 1600 --height 1200 \
	  --params '{"rings":28,"twist":2.7,"decay":2.1,"fold":1.15}'

render-batch:
	mrp batch --csv params/example_params.csv
