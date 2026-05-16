with daily_product as (
    select
        f.product_sk,
        p.product_id,
        p.product_name,
        p.category,
        f.order_date,
        sum(f.line_total) as daily_revenue,
        sum(f.quantity) as daily_units,
        count(distinct f.order_id) as daily_orders
    from {{ ref('ecom_dwd_order_line_di') }} f
    inner join {{ ref('ecom_dim_product') }} p
        on f.product_sk = p.product_sk
    where f.product_sk != -1
      and f.status != 'cancelled'
    group by f.product_sk, p.product_id, p.product_name, p.category, f.order_date
)

select
    product_sk,
    product_id,
    product_name,
    category,
    order_date,
    daily_revenue,
    daily_units,
    daily_orders,
    sum(daily_revenue) over (
        partition by product_sk
        order by order_date
        rows between 6 preceding and current row
    ) as revenue_7d,
    sum(daily_revenue) over (
        partition by product_sk
        order by order_date
        rows between 29 preceding and current row
    ) as revenue_30d,
    sum(daily_orders) over (
        partition by product_sk
        order by order_date
        rows between 6 preceding and current row
    ) as order_count_7d,
    sum(daily_orders) over (
        partition by product_sk
        order by order_date
        rows between 29 preceding and current row
    ) as order_count_30d
from daily_product
