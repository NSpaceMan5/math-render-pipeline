# Runbook - render runtime P99 jumped

## Symptom
`mrp_render_duration_seconds` P99 > 3x baseline; consumer throughput drops.

## Quick checks

    curl -s localhost:9100/metrics | grep mrp_render_duration_seconds

Compare buckets across formulas. Usually only one formula regresses.

## Root causes and fixes

| Cause | Fix |
|---|---|
| Heavy params (large rings, big nx*ny) | Cap params in producer; reject above threshold |
| CPU contention | Check docker stats; separate node for consumer |
| Memory swapping | Increase container memory; free caches |
| Sudden resolution spike (8K renders) | Enforce max-width in CLI/API |

## Tuning
- Runtime budget per formula: reject `rings > 64` at the producer.
- Cache repeated `(formula_id, params, w, h)`. The formula is deterministic;
  a second render is redundant.
