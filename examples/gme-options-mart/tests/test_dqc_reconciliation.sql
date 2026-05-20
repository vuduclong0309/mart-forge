with ods_count as (
    select count(*) as ods_rows
    from {{ ref('gme_ods_cboe_options_chain') }}
),
dwd_count as (
    select count(*) as dwd_rows
    from {{ ref('gme_dwd_option_contract_di') }}
)
select
    'dwd_exceeds_ods' as check_name,
    d.dwd_rows,
    o.ods_rows
from dwd_count d
cross join ods_count o
where d.dwd_rows > o.ods_rows
