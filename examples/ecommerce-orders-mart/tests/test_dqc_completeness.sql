-- DQC Control: Completeness / Volume
-- Verifies minimum expected row counts across key models.
with checks as (
    select 'raw_orders' as model, count(*) as cnt, 500 as min_expected
    from {{ ref('ecom_ods_raw_orders') }}
    union all
    select 'dim_customer', count(*), 50
    from {{ ref('ecom_dim_customer') }}
    union all
    select 'dim_product', count(*), 20
    from {{ ref('ecom_dim_product') }}
    union all
    select 'fact_order_line', count(*), 500
    from {{ ref('ecom_dwd_order_line_di') }}
)
select model, cnt, min_expected
from checks
where cnt < min_expected
