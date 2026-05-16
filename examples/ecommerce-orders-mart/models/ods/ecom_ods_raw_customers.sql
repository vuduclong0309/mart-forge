select
    customer_id,
    customer_name,
    email,
    city,
    state,
    tier,
    effective_date,
    'csv_seed' as provider,
    current_timestamp as pull_ts_utc,
    effective_date as quote_ts_utc,
    'seed-static' as run_id
from {{ ref('raw_customers') }}
