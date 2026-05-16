-- DWD Model Template
-- Layer: Detail-grain Wide fact table
-- Purpose: Atomically-grained transactions joined to all dimensions via
--          surrogate keys. This is the single source of truth for measures.
--
-- Naming: {{ mart.prefix }}_dwd_{{ grain_descriptor }}_{{ entity }}_di
-- Materialization: table (or incremental for high-volume sources)
-- Grain: {{ mart.grain }}
--
-- Key rules:
--   - Join to every dimension in the bus matrix via natural key -> surrogate key
--   - Use COALESCE(..., -1) for all FK columns (defaults to unknown member)
--   - SCD Type 2 joins must include date-range predicates
--   - No current_timestamp() in model logic (breaks idempotency)
--   - No SELECT * (explicit column list required)

with facts as (
    select
        {{ fact_business_key_1 }},
        {{ fact_business_key_2 }},
        {{ dimension_natural_key_1 }},
        {{ dimension_natural_key_2 }},
        {{ fact_date_column }},
        {{ measure_1 }},
        {{ measure_2 }},
        {{ measure_3 }},
        {{ status_column }}
    from {{ ref('{{ mart.prefix }}_ods_{{ source_name }}_{{ entity_name }}') }}
),

-- Dimension lookups: one CTE per dimension
-- Exclude unknown member rows from the lookup (they are the fallback)
{{ dimension_1_alias }} as (
    select {{ dimension_1_sk }}, {{ dimension_1_nk }}, effective_from, effective_to
    from {{ ref('{{ mart.prefix }}_dim_{{ dimension_1_name }}') }}
    where {{ dimension_1_nk }} != 'UNKNOWN'
),

{{ dimension_2_alias }} as (
    select {{ dimension_2_sk }}, {{ dimension_2_nk }}
    from {{ ref('{{ mart.prefix }}_dim_{{ dimension_2_name }}') }}
    where {{ dimension_2_nk }} != 'UNKNOWN'
),

dates as (
    select date_key, full_date
    from {{ ref('{{ mart.prefix }}_dim_date') }}
),

joined as (
    select
        -- Surrogate key for this fact table
        row_number() over (
            order by f.{{ fact_business_key_1 }}, f.{{ fact_business_key_2 }}
        ) as {{ fact_entity }}_sk,

        -- Business keys (preserved for debugging and reconciliation)
        f.{{ fact_business_key_1 }},
        f.{{ fact_business_key_2 }},

        -- Dimension foreign keys (default to -1 = unknown member)
        coalesce(d1.{{ dimension_1_sk }}, -1) as {{ dimension_1_sk }},
        coalesce(d2.{{ dimension_2_sk }}, -1) as {{ dimension_2_sk }},
        coalesce(dt.date_key, -1) as {{ fact_date_column }}_key,

        -- Degenerate dimensions (date preserved for convenience)
        f.{{ fact_date_column }},

        -- Measures
        f.{{ measure_1 }},
        f.{{ measure_2 }},
        f.{{ measure_3 }},

        -- Status / flags
        f.{{ status_column }}

    from facts f

    -- SCD Type 2 dimension join (with date-range predicate)
    left join {{ dimension_1_alias }} d1
        on f.{{ dimension_natural_key_1 }} = d1.{{ dimension_1_nk }}
        and f.{{ fact_date_column }} >= d1.effective_from
        and f.{{ fact_date_column }} <= d1.effective_to

    -- SCD Type 1 dimension join (simple natural key match)
    left join {{ dimension_2_alias }} d2
        on f.{{ dimension_natural_key_2 }} = d2.{{ dimension_2_nk }}

    -- Date dimension join
    left join dates dt
        on f.{{ fact_date_column }} = dt.full_date
)

select * from joined
