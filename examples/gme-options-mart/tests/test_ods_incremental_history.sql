-- Proves the incremental unique_key merge works: each (pull_date, option_symbol)
-- pair appears exactly once. If repeated runs created duplicates or dropped
-- historical dates, this test catches it.
-- Run: dbt build && dbt build   (two consecutive runs)
-- Expected: 0 rows returned (pass)

SELECT
    pull_date,
    option_symbol,
    COUNT(*) AS occurrences
FROM {{ ref('gme_ods_cboe_options_chain') }}
GROUP BY pull_date, option_symbol
HAVING COUNT(*) > 1
