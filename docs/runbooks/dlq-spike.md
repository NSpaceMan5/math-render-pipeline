# Runbook - DLQ spike

## Symptom
Grafana alert `MRP consumer DLQ spike`. Rate > 5/min for 2 minutes.

## Quick checks

    docker compose exec redpanda rpk topic consume render.events.dlq --num 20

Each payload contains: error, attempts, correlation_id, raw.

## Classify by error prefix

| Prefix | Meaning | Typical cause |
|---|---|---|
| parse: | Malformed JSON or missing field | Producer bug or schema drift |
| insert: | DB insert failed after retries | Postgres down, disk full, constraint |

## Root causes and fixes
- Producer bug: fix the producer, replay the DLQ:

      python scripts/replay_dlq.py --topic render.events.dlq

- Transient Postgres failure: DLQ should drain once DB is back. Verify with
  `docker compose logs consumer | grep dlq`.

- Schema mismatch: `alembic upgrade head`, then restart consumer.

## After the fix
Confirm DLQ rate returns to 0. Do not purge the DLQ without inspecting the
error field first. It is the audit trail.
