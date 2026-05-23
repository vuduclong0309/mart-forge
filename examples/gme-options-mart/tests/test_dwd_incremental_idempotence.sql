-- Proves delete+insert keeps DWD idempotent: each (pull_date, option_symbol)
-- pair appears exactly once. Run: dbt build && dbt build (two consecutive runs)
-- Expected: 0 rows returned (pass)

SELECT
    pull_date,
    option_symbol,
    COUNT(*) AS occurrences
FROM {{ ref('gme_dwd_option_contract_di') }}
GROUP BY pull_date, option_symbol
HAVING COUNT(*) > 1
