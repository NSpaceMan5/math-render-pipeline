# Runbook - consumer lag

## Symptom
`render.events` consumer group lag keeps growing; downstream freshness degrades.

## Quick checks

    docker compose exec redpanda rpk group describe mrp-consumer

Look at LAG per partition.

Consumer metrics (if METRICS_PORT exposed):

    curl -s localhost:9100/metrics | grep mrp_consumer_

## Root causes and fixes

| Cause | Fix |
|---|---|
| Insert is slow (DB contention) | Check pg_stat_activity; add index; scale vertically |
| Poison-pill loop on one event | Confirm DLQ is draining (rpk topic consume render.events.dlq) |
| Consumer OOM / crash-loop | Reduce batch size; raise memory limit |
| Downstream Postgres throttled | Check connection pool; reduce max_retries backoff |

## Scaling
- Increase consumer parallelism (same KAFKA_GROUP):

      docker compose up -d --scale consumer=N

- Repartition the topic if N exceeds current partition count.

## After the fix
Watch lag return to zero. Grafana panel `Stream events per minute` should show
throughput catching up.
