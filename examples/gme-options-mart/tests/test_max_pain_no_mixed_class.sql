-- Verify headline max pain in daily snapshot is from a single standard-class expiry,
-- not an all-expiry or mixed-class calculation.
-- Returns rows (failures) where max_pain_expiry is NULL — meaning the snapshot
-- could not resolve to a specific standard expiry.
SELECT
    pull_date,
    max_pain_strike,
    max_pain_expiry
FROM {{ ref('gme_dws_daily_snapshot_1d') }}
WHERE max_pain_strike IS NOT NULL
  AND max_pain_expiry IS NULL
