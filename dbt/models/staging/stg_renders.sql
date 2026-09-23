select
    render_id, formula_id, formula_hash,
    coalesce((params_json->>'rings')::int,     0) as rings,
    coalesce((params_json->>'twist')::numeric, 0) as twist,
    coalesce((params_json->>'decay')::numeric, 0) as decay,
    coalesce((params_json->>'fold')::numeric,  0) as fold,
    coalesce((params_json->>'nx')::int,        0) as nx,
    coalesce((params_json->>'ny')::int,        0) as ny,
    width, height, runtime_ms, checksum, storage_uri, preview_uri,
    bytes_full, bytes_preview, ingest_source, created_at,
    date_trunc('day', created_at) as render_day
from {{ source('mrp', 'render_events') }}
