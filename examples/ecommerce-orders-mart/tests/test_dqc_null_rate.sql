-- DQC Control: Null-Rate Threshold
-- Verifies non-PK columns do not exceed 5% null rate in the fact table.
with total as (
    select count(*) as total_rows from {{ ref('ecom_dwd_order_line_di') }}
),
null_checks as (
    select
        'quantity' as column_name,
        count(*) filter (where quantity is null) as null_count
    from {{ ref('ecom_dwd_order_line_di') }}
    union all
    select
        'unit_price',
        count(*) filter (where unit_price is null)
    from {{ ref('ecom_dwd_order_line_di') }}
    union all
    select
        'line_total',
        count(*) filter (where line_total is null)
    from {{ ref('ecom_dwd_order_line_di') }}
    union all
    select
        'status',
        count(*) filter (where status is null)
    from {{ ref('ecom_dwd_order_line_di') }}
)
select
    nc.column_name,
    nc.null_count,
    t.total_rows,
    round(nc.null_count::double / t.total_rows, 4) as null_rate
from null_checks nc
cross join total t
where nc.null_count::double / t.total_rows > 0.05
