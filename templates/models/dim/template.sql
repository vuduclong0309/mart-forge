-- DIM Model Template
-- Layer: Dimension
-- Purpose: Descriptive context table with surrogate keys and SCD handling.
--
-- Naming: {{ mart.prefix }}_dim_{{ entity_name }}
-- Materialization: table (full rebuild each run for correctness)
-- Grain: One row per {{ entity_name }} (Type 1) or one row per
--        {{ entity_name }} per effective period (Type 2).
--
-- SCD Support:
--   - Type 0 (static): Remove the ranked/scd2 CTEs, select directly from source
--   - Type 1 (overwrite): Use the with_sk CTE only, no effective dates
--   - Type 2 (history): Use the full template below with ranked + scd2 CTEs
--
-- Usage:
--   1. Replace {{ ... }} placeholders with actual values
--   2. Choose SCD type and remove unused CTEs
--   3. Always include the unknown_member CTE

-- =====================================================================
-- SCD TYPE 2 TEMPLATE (with history tracking)
-- Remove the ranked + scd2 CTEs for Type 0 or Type 1.
-- =====================================================================

with source as (
    select
        {{ natural_key }},
        {{ attribute_1 }},
        {{ attribute_2 }},
        {{ attribute_3 }},
        {{ effective_date_column }}
    from {{ ref('{{ mart.prefix }}_ods_{{ source_name }}_{{ entity_name_plural }}') }}
),

-- SCD Type 2: Rank versions by effective date to compute validity windows.
-- For Type 1, replace this section with a simple select + row_number for SK.
ranked as (
    select
        *,
        row_number() over (
            partition by {{ natural_key }} order by {{ effective_date_column }}
        ) as rn,
        lead({{ effective_date_column }}) over (
            partition by {{ natural_key }} order by {{ effective_date_column }}
        ) as next_effective_date
    from source
),

scd2 as (
    select
        -- Surrogate key: unique per version row
        row_number() over (
            order by {{ natural_key }}, {{ effective_date_column }}
        ) as {{ entity_name }}_sk,

        -- Natural key: same across all versions of the same entity
        {{ natural_key }},

        -- Descriptive attributes
        {{ attribute_1 }},
        {{ attribute_2 }},
        {{ attribute_3 }},

        -- SCD Type 2 validity columns
        {{ effective_date_column }} as effective_from,
        coalesce(
            next_effective_date - interval '1 day',
            date '2099-12-31'
        )::date as effective_to,
        case
            when next_effective_date is null then true
            else false
        end as is_current
    from ranked
),

-- =====================================================================
-- UNKNOWN MEMBER (mandatory for every dimension)
-- Fact rows with missing dimension references default to sk = -1.
-- Adjust placeholder values to match your column types.
-- =====================================================================
unknown_member as (
    select
        -1 as {{ entity_name }}_sk,
        'UNKNOWN' as {{ natural_key }},
        'Unknown' as {{ attribute_1 }},
        'Unknown' as {{ attribute_2 }},
        'Unknown' as {{ attribute_3 }},
        date '1900-01-01' as effective_from,
        date '2099-12-31' as effective_to,
        true as is_current
)

select * from scd2
union all
select * from unknown_member


-- =====================================================================
-- SCD TYPE 1 ALTERNATIVE
-- Uncomment and use this instead of the ranked/scd2 CTEs above
-- if you don't need history tracking.
-- =====================================================================
--
-- with source as (
--     select
--         {{ natural_key }},
--         {{ attribute_1 }},
--         {{ attribute_2 }},
--         {{ attribute_3 }}
--     from {{ ref('{{ mart.prefix }}_ods_{{ source_name }}_{{ entity_name_plural }}') }}
-- ),
--
-- with_sk as (
--     select
--         row_number() over (order by {{ natural_key }}) as {{ entity_name }}_sk,
--         {{ natural_key }},
--         {{ attribute_1 }},
--         {{ attribute_2 }},
--         {{ attribute_3 }}
--     from source
-- ),
--
-- unknown_member as (
--     select
--         -1 as {{ entity_name }}_sk,
--         'UNKNOWN' as {{ natural_key }},
--         'Unknown' as {{ attribute_1 }},
--         'Unknown' as {{ attribute_2 }},
--         'Unknown' as {{ attribute_3 }}
-- )
--
-- select * from with_sk
-- union all
-- select * from unknown_member
