select
    pull_date,
    option_symbol,
    count(*) as row_count
from {{ ref('gme_dwd_option_contract_di') }}
group by pull_date, option_symbol
having count(*) > 1
