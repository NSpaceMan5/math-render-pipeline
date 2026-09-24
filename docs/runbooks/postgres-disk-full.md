# Runbook - Postgres disk nearly full

## Symptom
Postgres errors: `could not extend file`, `No space left on device`.
Consumer DLQ fills up.

## Quick checks

    docker compose exec postgres df -h /var/lib/postgresql/data
    docker compose exec postgres du -sh /var/lib/postgresql/data/pg_wal
    docker compose exec postgres psql -U mrp -c "SELECT pg_size_pretty(pg_total_relation_size('render_events'));"

## Common causes and fixes

| Cause | Fix |
|---|---|
| WAL accumulation | SELECT pg_switch_wal(); check replication slots |
| Bloat in render_events | VACUUM (FULL, ANALYZE) render_events; |
| Genuine growth | Archive old rows to Parquet, then DELETE in batches |

## Long term
- Prune old rows in batches of 10k to avoid long locks:

      DELETE FROM render_events
      WHERE created_at < now() - interval '365 days';

- The Parquet mirror in `data/parquet/` is the analytical archive.
  The DB only needs recent rows.
