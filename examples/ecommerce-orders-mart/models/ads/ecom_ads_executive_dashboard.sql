with daily_rev as (
    select * from {{ ref('ecom_dws_daily_revenue_1d') }}
),

customer_ltv as (
    select * from {{ ref('ecom_dws_customer_lifetime_td') }}
),

date_dim as (
    select * from {{ ref('ecom_dim_date') }}
),

daily_enriched as (
    select
        d.date_key,
        d.full_date,
        d.year,
        d.quarter,
        d.month,
        d.month_name,
        d.day_name,
        d.is_weekend,
        d.is_holiday,
        coalesce(r.order_count, 0) as order_count,
        coalesce(r.total_revenue, 0) as total_revenue,
        coalesce(r.total_units, 0) as total_units,
        coalesce(r.avg_order_value, 0) as avg_order_value,
        sum(coalesce(r.total_revenue, 0)) over (
            partition by d.year, d.month
            order by d.full_date
        ) as mtd_revenue,
        sum(coalesce(r.total_revenue, 0)) over (
            partition by d.year
            order by d.full_date
        ) as ytd_revenue
    from date_dim d
    left join daily_rev r
        on d.date_key = r.order_date_key
    where d.full_date between (select min(order_date) from {{ ref('ecom_dwd_order_line_di') }})
                          and (select max(order_date) from {{ ref('ecom_dwd_order_line_di') }})
),

summary as (
    select
        (select count(distinct customer_id) from customer_ltv) as total_customers,
        (select sum(total_revenue) from customer_ltv) as grand_total_revenue,
        (select round(avg(total_revenue), 2) from customer_ltv) as avg_customer_ltv,
        (select count(distinct customer_id) from customer_ltv where total_orders >= 3) as repeat_customers
)

select
    de.*,
    s.total_customers,
    s.grand_total_revenue,
    s.avg_customer_ltv,
    s.repeat_customers
from daily_enriched de
cross join summary s
