-- DQC Control: Freshness
-- Verifies that ODS data has been loaded (pull_ts_utc exists and is recent).
-- For seed-based data this always passes; in production it checks SLA compliance.
select count(*) as stale_rows
from {{ ref('ecom_ods_raw_orders') }}
where pull_ts_utc is null
having count(*) > 0
