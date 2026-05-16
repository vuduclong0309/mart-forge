-- DWS Model Template
-- Layer: Summary / Aggregation
-- Purpose: Pre-computed rollups at coarser grains with time-window semantics.
--
-- Naming: {{ mart.prefix }}_dws_{{ dimension_axis }}_{{ metric_group }}_{{ window_suffix }}
-- Materialization: table (full rebuild each run — not incremental)
-- Grain: One row per {{ aggregation_grain }}
--
-- Window suffix convention:
--   _1d  = daily snapshot (one row per day)
--   _nd  = N-day rolling windows (7d, 30d via window functions)
--   _td  = to-date / lifetime (cumulative, no time boundary)
--   _mtd = month-to-date (resets each calendar month)
--
-- Key rules:
--   - Always aggregate from DWD models (never directly from ODS)
--   - Filter excluded records (cancelled, deleted) BEFORE aggregation
--   - No current_timestamp() in model logic
--   - Materialized as table for correctness

-- =====================================================================
-- VARIANT A: Daily Snapshot (_1d)
-- One row per day with aggregated measures.
-- =====================================================================

-- select
--     {{ date_key_column }},
--     {{ date_column }},
--     count(distinct {{ count_distinct_column }}) as {{ count_measure_name }},
--     sum({{ sum_column }}) as {{ sum_measure_name }},
--     sum({{ quantity_column }}) as {{ quantity_measure_name }},
--     round(
--         sum({{ sum_column }}) / nullif(count(distinct {{ count_distinct_column }}), 0),
--         2
--     ) as {{ avg_measure_name }}
-- from {{ ref('{{ mart.prefix }}_dwd_{{ fact_model_name }}') }}
-- where {{ status_column }} != 'cancelled'
-- group by {{ date_key_column }}, {{ date_column }}

-- =====================================================================
-- VARIANT B: To-Date / Lifetime (_td)
-- One row per entity with all-time cumulative measures.
-- =====================================================================

-- with entity_activity as (
--     select
--         f.{{ entity_sk }},
--         d.{{ entity_nk }},
--         d.{{ entity_attribute }},
--         f.{{ count_distinct_column }},
--         f.{{ date_column }},
--         f.{{ sum_column }},
--         f.{{ quantity_column }},
--         f.{{ status_column }}
--     from {{ ref('{{ mart.prefix }}_dwd_{{ fact_model_name }}') }} f
--     inner join {{ ref('{{ mart.prefix }}_dim_{{ entity_name }}') }} d
--         on f.{{ entity_sk }} = d.{{ entity_sk }}
--         and d.is_current = true
--     where f.{{ entity_sk }} != -1
--       and f.{{ status_column }} != 'cancelled'
-- )
--
-- select
--     {{ entity_sk }},
--     {{ entity_nk }},
--     {{ entity_attribute }},
--     count(distinct {{ count_distinct_column }}) as total_{{ count_measure_name }},
--     sum({{ sum_column }}) as total_{{ sum_measure_name }},
--     sum({{ quantity_column }}) as total_{{ quantity_measure_name }},
--     min({{ date_column }}) as first_{{ date_column }},
--     max({{ date_column }}) as last_{{ date_column }},
--     round(
--         sum({{ sum_column }}) / nullif(count(distinct {{ count_distinct_column }}), 0),
--         2
--     ) as avg_{{ sum_measure_name }}
-- from entity_activity
-- group by {{ entity_sk }}, {{ entity_nk }}, {{ entity_attribute }}

-- =====================================================================
-- VARIANT C: N-Day Rolling Windows (_nd)
-- One row per entity per day with rolling 7d and 30d window columns.
-- =====================================================================

with daily_entity as (
    select
        f.{{ entity_sk }},
        d.{{ entity_nk }},
        d.{{ entity_attribute_1 }},
        d.{{ entity_attribute_2 }},
        f.{{ date_column }},
        sum(f.{{ sum_column }}) as daily_{{ sum_measure_name }},
        sum(f.{{ quantity_column }}) as daily_{{ quantity_measure_name }},
        count(distinct f.{{ count_distinct_column }}) as daily_{{ count_measure_name }}
    from {{ ref('{{ mart.prefix }}_dwd_{{ fact_model_name }}') }} f
    inner join {{ ref('{{ mart.prefix }}_dim_{{ entity_name }}') }} d
        on f.{{ entity_sk }} = d.{{ entity_sk }}
    where f.{{ entity_sk }} != -1
      and f.{{ status_column }} != 'cancelled'
    group by
        f.{{ entity_sk }},
        d.{{ entity_nk }},
        d.{{ entity_attribute_1 }},
        d.{{ entity_attribute_2 }},
        f.{{ date_column }}
)

select
    {{ entity_sk }},
    {{ entity_nk }},
    {{ entity_attribute_1 }},
    {{ entity_attribute_2 }},
    {{ date_column }},
    daily_{{ sum_measure_name }},
    daily_{{ quantity_measure_name }},
    daily_{{ count_measure_name }},

    -- 7-day rolling windows
    sum(daily_{{ sum_measure_name }}) over (
        partition by {{ entity_sk }}
        order by {{ date_column }}
        rows between 6 preceding and current row
    ) as {{ sum_measure_name }}_7d,

    -- 30-day rolling windows
    sum(daily_{{ sum_measure_name }}) over (
        partition by {{ entity_sk }}
        order by {{ date_column }}
        rows between 29 preceding and current row
    ) as {{ sum_measure_name }}_30d,

    -- Rolling order/event counts
    sum(daily_{{ count_measure_name }}) over (
        partition by {{ entity_sk }}
        order by {{ date_column }}
        rows between 6 preceding and current row
    ) as {{ count_measure_name }}_7d,

    sum(daily_{{ count_measure_name }}) over (
        partition by {{ entity_sk }}
        order by {{ date_column }}
        rows between 29 preceding and current row
    ) as {{ count_measure_name }}_30d

from daily_entity
