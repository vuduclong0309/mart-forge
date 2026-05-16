with orders as (
    select
        order_id,
        line_id,
        customer_id,
        product_id,
        order_date,
        quantity,
        unit_price,
        line_total,
        status
    from {{ ref('ecom_ods_raw_orders') }}
),

customers as (
    select customer_sk, customer_id, effective_from, effective_to
    from {{ ref('ecom_dim_customer') }}
    where customer_id != 'UNKNOWN'
),

products as (
    select product_sk, product_id
    from {{ ref('ecom_dim_product') }}
    where product_id != 'UNKNOWN'
),

dates as (
    select date_key, full_date
    from {{ ref('ecom_dim_date') }}
),

joined as (
    select
        row_number() over (
            order by o.order_id, o.line_id
        ) as order_line_sk,
        o.order_id,
        o.line_id,
        coalesce(c.customer_sk, -1) as customer_sk,
        coalesce(p.product_sk, -1) as product_sk,
        coalesce(d.date_key, -1) as order_date_key,
        o.order_date,
        o.quantity,
        o.unit_price,
        o.line_total,
        o.status
    from orders o
    left join customers c
        on o.customer_id = c.customer_id
        and o.order_date >= c.effective_from
        and o.order_date <= c.effective_to
    left join products p
        on o.product_id = p.product_id
    left join dates d
        on o.order_date = d.full_date
)

select * from joined
