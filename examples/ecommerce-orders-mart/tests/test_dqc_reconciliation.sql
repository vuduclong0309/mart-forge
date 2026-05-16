-- DQC Control: Business Reconciliation
-- Compares mart revenue totals against seed CSV totals (tolerance: 0.01).
with seed_totals as (
    select
        sum(line_total) as seed_revenue,
        count(distinct order_id) as seed_order_count
    from {{ ref('raw_orders') }}
    where status != 'cancelled'
),
mart_totals as (
    select
        sum(line_total) as mart_revenue,
        count(distinct order_id) as mart_order_count
    from {{ ref('ecom_dwd_order_line_di') }}
    where status != 'cancelled'
)
select
    'revenue_mismatch' as check_name,
    s.seed_revenue,
    m.mart_revenue,
    abs(s.seed_revenue - m.mart_revenue) as diff
from seed_totals s
cross join mart_totals m
where abs(s.seed_revenue - m.mart_revenue) > 0.01

union all

select
    'order_count_mismatch',
    s.seed_order_count,
    m.mart_order_count,
    abs(s.seed_order_count - m.mart_order_count)
from seed_totals s
cross join mart_totals m
where s.seed_order_count != m.mart_order_count
