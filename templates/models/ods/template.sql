-- ODS Model Template
-- Layer: Operational Data Store
-- Purpose: Thin 1:1 mapping from raw source with provenance columns.
--          No business logic, no joins, no transformations beyond aliasing.
--
-- Naming: {{ mart.prefix }}_ods_{{ source_name }}_{{ entity_name }}
-- Materialization: view (for seeds) or incremental (for live sources)
-- Grain: Matches the source table grain exactly.
--
-- Usage:
--   1. Replace {{ ... }} placeholders with actual values
--   2. List ALL source columns explicitly (no SELECT *)
--   3. Keep provenance columns at the end of the SELECT
--   4. For incremental sources, uncomment the is_incremental block

-- {{ config(materialized='view') }}
-- For incremental sources, use:
-- {{ config(materialized='incremental', unique_key='{{ primary_key_columns }}') }}

select
    -- =================================================================
    -- Source columns (explicit list — no SELECT *)
    -- Replace these with actual columns from your source table.
    -- =================================================================
    {{ primary_key_column_1 }},
    {{ primary_key_column_2 }},
    {{ business_column_1 }},
    {{ business_column_2 }},
    {{ business_column_3 }},
    -- ... add all source columns here ...

    -- =================================================================
    -- Provenance columns (mandatory on every ODS model)
    -- These track data lineage: where it came from, when, and which run.
    -- =================================================================
    '{{ providers.primary }}' as provider,
    current_timestamp as pull_ts_utc,
    {{ source_timestamp_column }} as quote_ts_utc,
    '{{ var("run_id", "manual") }}' as run_id

from {{ ref('{{ raw_seed_or_source }}') }}

-- =================================================================
-- Incremental filter (uncomment for live sources)
-- Only processes rows newer than the last successful load.
-- =================================================================
-- {% if is_incremental() %}
-- where {{ source_timestamp_column }} > (select max(quote_ts_utc) from {{ this }})
-- {% endif %}
