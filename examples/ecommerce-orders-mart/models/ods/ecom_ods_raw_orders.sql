select
    order_id,
    line_id,
    customer_id,
    product_id,
    order_date,
    quantity,
    unit_price,
    line_total,
    status,
    'csv_seed' as provider,
    current_timestamp as pull_ts_utc,
    order_date as quote_ts_utc,
    'seed-static' as run_id
from {{ ref('raw_orders') }}
