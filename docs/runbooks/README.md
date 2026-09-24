# Runbooks

Operational playbooks for common incidents. Each file lists symptoms,
quick checks, root causes, and the fix.

| Incident | File |
|---|---|
| Render table is stale | stale-freshness.md |
| Consumer lags behind producer | consumer-lag.md |
| DLQ spike | dlq-spike.md |
| Postgres disk nearly full | postgres-disk-full.md |
| Render runtime P99 jumped | high-runtime.md |

Dashboards: Grafana -> MRP folder.
Metrics: http://<consumer-host>:9100/metrics
Traces: any OTLP backend (Jaeger, Tempo, Honeycomb) if
OTEL_EXPORTER_OTLP_ENDPOINT is set.
