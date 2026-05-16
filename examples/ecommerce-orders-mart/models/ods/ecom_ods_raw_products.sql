select
    product_id,
    product_name,
    category,
    subcategory,
    unit_price,
    supplier,
    'csv_seed' as provider,
    current_timestamp as pull_ts_utc,
    current_timestamp as quote_ts_utc,
    'seed-static' as run_id
from {{ ref('raw_products') }}
