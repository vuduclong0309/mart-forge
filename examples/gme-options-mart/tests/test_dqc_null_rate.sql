with total as (
    select count(*) as total_rows from {{ ref('gme_dwd_option_contract_di') }}
),
null_checks as (
    select
        'implied_vol' as column_name,
        count(*) filter (where implied_vol is null) as null_count
    from {{ ref('gme_dwd_option_contract_di') }}
    union all
    select
        'delta',
        count(*) filter (where delta is null)
    from {{ ref('gme_dwd_option_contract_di') }}
    union all
    select
        'gamma',
        count(*) filter (where gamma is null)
    from {{ ref('gme_dwd_option_contract_di') }}
    union all
    select
        'mid_price',
        count(*) filter (where mid_price is null)
    from {{ ref('gme_dwd_option_contract_di') }}
)
select
    nc.column_name,
    nc.null_count,
    t.total_rows,
    round(nc.null_count::double / t.total_rows, 4) as null_rate
from null_checks nc
cross join total t
where nc.null_count::double / t.total_rows > 0.05
