select
    order_date_key,
    order_date,
    count(distinct order_id) as order_count,
    sum(line_total) as total_revenue,
    sum(quantity) as total_units,
    round(sum(line_total) / nullif(count(distinct order_id), 0), 2) as avg_order_value
from {{ ref('ecom_dwd_order_line_di') }}
where status != 'cancelled'
group by order_date_key, order_date
