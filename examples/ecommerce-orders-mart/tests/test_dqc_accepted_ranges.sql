-- DQC Control: Accepted Ranges
-- Verifies numeric metrics are within plausible bounds.
select 'negative_quantity' as violation, count(*) as cnt
from {{ ref('ecom_dwd_order_line_di') }}
where quantity <= 0
having count(*) > 0

union all

select 'negative_unit_price', count(*)
from {{ ref('ecom_dwd_order_line_di') }}
where unit_price < 0
having count(*) > 0

union all

select 'negative_line_total', count(*)
from {{ ref('ecom_dwd_order_line_di') }}
where line_total < 0
having count(*) > 0

union all

select 'negative_daily_revenue', count(*)
from {{ ref('ecom_dws_daily_revenue_1d') }}
where total_revenue < 0
having count(*) > 0
