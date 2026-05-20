with checks as (
    select 'ods_options_chain' as model, count(*) as cnt, 100 as min_expected
    from {{ ref('gme_ods_cboe_options_chain') }}
    union all
    select 'dwd_option_contract', count(*), 50
    from {{ ref('gme_dwd_option_contract_di') }}
    union all
    select 'dws_strike_gex', count(*), 10
    from {{ ref('gme_dws_strike_gex_1d') }}
    union all
    select 'dws_daily_snapshot', count(*), 1
    from {{ ref('gme_dws_daily_snapshot_1d') }}
)
select model, cnt, min_expected
from checks
where cnt < min_expected
