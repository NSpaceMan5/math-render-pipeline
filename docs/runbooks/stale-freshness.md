# Runbook - stale freshness

## Symptom
Grafana alert `MRP render_events is stale`. No new rows for more than 6h.

## Quick checks

1. Is the DAG paused?

       airflow dags list-runs -d math_render_pipeline | head

2. Is the consumer running?

       docker compose ps consumer
       docker compose logs --tail=200 consumer | grep -E "error|dlq"

3. Is the producer still publishing?

       docker compose exec redpanda rpk topic describe render.events

   Look at High-Watermark. If it stopped advancing, upstream is silent.

## Root causes and fixes

| Cause | Fix |
|---|---|
| DAG paused / failing | Unpause, check Airflow logs, retry the run |
| Consumer crashed | docker compose restart consumer; check OOM in docker stats |
| Producer idle (no inputs) | Expected if params CSV was not updated |
| Postgres unreachable | psql $POSTGRES_DSN -c "select 1"; restore DB if needed |

## After the fix
- Confirm freshness recovers:

      python data_quality/run_checks.py --max-age-hours 2

- If the outage exceeded retention, backfill:

      airflow dags backfill math_render_pipeline --start-date <date> --end-date <date>
