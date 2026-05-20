select count(*) as stale_rows
from {{ ref('gme_ods_cboe_options_chain') }}
where pull_ts_utc is null
having count(*) > 0
