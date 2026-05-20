select 'negative_strike' as violation, count(*) as cnt
from {{ ref('gme_dwd_option_contract_di') }}
where strike <= 0
having count(*) > 0

union all

select 'negative_open_interest', count(*)
from {{ ref('gme_dwd_option_contract_di') }}
where open_interest < 0
having count(*) > 0

union all

select 'negative_spot', count(*)
from {{ ref('gme_dws_daily_snapshot_1d') }}
where spot <= 0
having count(*) > 0

union all

select 'pc_ratio_out_of_range', count(*)
from {{ ref('gme_dws_daily_snapshot_1d') }}
where pc_ratio < 0 or pc_ratio > 50
having count(*) > 0
