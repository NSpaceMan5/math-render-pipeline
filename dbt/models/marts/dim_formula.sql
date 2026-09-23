select distinct formula_hash, formula_id, rings, twist, decay, fold, nx, ny
from {{ ref('stg_renders') }}
