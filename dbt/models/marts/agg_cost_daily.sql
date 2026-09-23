select
    render_day,
    count(*) as renders,
    sum(pixels) / 1e6 as total_megapixels,
    sum(runtime_ms) / 1000.0 as total_cpu_seconds,
    sum(runtime_ms) / 60000.0 as total_cpu_minutes,
    avg(runtime_ms) as avg_runtime_ms,
    sum(bytes_full) / 1024.0 / 1024.0 as total_mb_stored,
    count(distinct formula_hash) as distinct_formulas
from {{ ref('fct_render_events') }}
group by render_day
order by render_day
