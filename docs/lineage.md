# Data lineage

Emitted via [OpenLineage](https://openlineage.io/) and viewable in
[Marquez](https://marquezproject.ai/).

## What gets emitted

| Job | Event type | Inputs | Outputs |
|---|---|---|---|
| `render` | START / COMPLETE / FAIL | `spec/<formula>/<hash>` | `renders/<id>`, storage URI |
| `consume` | COMPLETE | `topic/render.events` | `table/render_events/<id>` |

Each render produces three events (START, COMPLETE or FAIL, plus a
consumer COMPLETE once the stream ingests it).

## Enable

    docker compose up -d marquez-db marquez marquez-web
    export OPENLINEAGE_URL=http://localhost:5000
    mrp run --formula polar_loom --width 400 --height 300

Open the Marquez UI at <http://localhost:8888>. You should see:
- Namespace: `mrp`
- Jobs: `render`, `consume`
- Datasets: one per spec hash, one per render, plus the topic and table

## Disable

Unset `OPENLINEAGE_URL` (or leave it empty). The emitter logs once at
DEBUG and becomes a no-op. No code changes required.

    unset OPENLINEAGE_URL
    mrp run --formula polar_loom --width 400 --height 300

## Architecture
mrp run ──▶ renderer ──▶ OpenLineage emitter ──▶ Marquez API ──▶ Marquez Web
│
└──▶ PNG + metadata (existing path, unchanged)

mrp consume ──▶ consumer ──▶ OpenLineage emitter ──▶ Marquez API

Lineage is best-effort: emit failures are logged at WARNING and never
propagate. The render succeeds even if Marquez is down.
