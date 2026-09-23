select
    render_id, formula_hash, formula_id,
    rings, twist, decay, fold, nx, ny, width, height,
    (width * height) as pixels, runtime_ms,
    round(runtime_ms::numeric / nullif(width::numeric * height, 0) * 1e6, 2) as us_per_megapixel,
    bytes_full, bytes_preview,
    round(bytes_full::numeric / nullif(width::numeric * height, 0) * 1e6, 2) as bytes_per_megapixel,
    storage_uri, render_day
from {{ ref('stg_renders') }}
