with customer_orders as (
    select
        f.customer_sk,
        c.customer_id,
        c.customer_name,
        c.tier as current_tier,
        f.order_id,
        f.order_date,
        f.line_total,
        f.quantity,
        f.status
    from {{ ref('ecom_dwd_order_line_di') }} f
    inner join {{ ref('ecom_dim_customer') }} c
        on f.customer_sk = c.customer_sk
        and c.is_current = true
    where f.customer_sk != -1
      and f.status != 'cancelled'
)

select
    customer_sk,
    customer_id,
    customer_name,
    current_tier,
    count(distinct order_id) as total_orders,
    sum(line_total) as total_revenue,
    sum(quantity) as total_units,
    min(order_date) as first_order_date,
    max(order_date) as last_order_date,
    round(sum(line_total) / nullif(count(distinct order_id), 0), 2) as avg_order_value
from customer_orders
group by customer_sk, customer_id, customer_name, current_tier
