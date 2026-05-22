-- ADS Model Template
-- Layer: Application Data Service (One-Big-Table)
-- Purpose: Wide denormalized table for a specific consumer. Combines
--          DWS aggregations, DWD details, and DIM attributes into a
--          single flat table optimized for downstream queries.
--
-- Naming: {{ mart.prefix }}_ads_{{ consumer }}_{{ purpose }}
-- Materialization: table (full rebuild each run)
-- Grain: {{ ads_grain }}
--
-- Key rules:
--   - Joins DWS and/or DWD to DIM tables (never reads ODS directly)
--   - OK to include both detail and summary columns
--   - OK to include running totals (MTD, YTD) via window functions
--   - Consumer should be able to query this table alone without joins
--   - No current_timestamp() in model logic

-- =====================================================================
-- Source CTEs: one per upstream model
-- =====================================================================

with primary_summary as (
    -- FIXME(select-star): replace * with the explicit columns your mart needs
    select * from {{ ref('{{ mart.prefix }}_dws_{{ primary_dws_model }}') }}
),

secondary_summary as (
    -- FIXME(select-star): replace * with the explicit columns your mart needs
    select * from {{ ref('{{ mart.prefix }}_dws_{{ secondary_dws_model }}') }}
),

date_dim as (
    -- FIXME(select-star): replace * with the explicit columns your mart needs
    select * from {{ ref('{{ mart.prefix }}_dim_date') }}
),

-- =====================================================================
-- Enrichment: Join date dimension to primary summary for calendar attrs
-- =====================================================================

enriched as (
    select
        -- Date dimension attributes (enables filter/group by month, quarter, etc.)
        d.date_key,
        d.full_date,
        d.year,
        d.quarter,
        d.month,
        d.month_name,
        d.day_name,
        d.is_weekend,
        d.is_holiday,

        -- Primary measures (from DWS)
        coalesce(p.{{ primary_measure_1 }}, 0) as {{ primary_measure_1 }},
        coalesce(p.{{ primary_measure_2 }}, 0) as {{ primary_measure_2 }},
        coalesce(p.{{ primary_measure_3 }}, 0) as {{ primary_measure_3 }},
        coalesce(p.{{ primary_measure_4 }}, 0) as {{ primary_measure_4 }},

        -- Running totals (computed via window functions)
        sum(coalesce(p.{{ primary_measure_1 }}, 0)) over (
            partition by d.year, d.month
            order by d.full_date
        ) as mtd_{{ primary_measure_1 }},

        sum(coalesce(p.{{ primary_measure_1 }}, 0)) over (
            partition by d.year
            order by d.full_date
        ) as ytd_{{ primary_measure_1 }}

    from date_dim d
    left join primary_summary p
        on d.{{ date_join_key }} = p.{{ primary_date_key }}

    -- Limit to the active date range (no empty future rows)
    where d.full_date between
        (select min({{ fact_date_column }}) from {{ ref('{{ mart.prefix }}_dwd_{{ fact_model }}') }})
        and
        (select max({{ fact_date_column }}) from {{ ref('{{ mart.prefix }}_dwd_{{ fact_model }}') }})
),

-- =====================================================================
-- Cross-join summary stats from secondary DWS
-- These are scalar values that appear on every row (dashboard KPIs)
-- =====================================================================

summary_stats as (
    select
        count(distinct {{ entity_nk }}) as total_{{ entity_name_plural }},
        sum({{ lifetime_measure }}) as grand_total_{{ lifetime_measure }},
        round(avg({{ lifetime_measure }}), 2) as avg_{{ entity_name }}_{{ lifetime_measure }},
        count(distinct {{ entity_nk }}) filter (
            where {{ repeat_threshold_column }} >= {{ repeat_threshold_value }}
        ) as repeat_{{ entity_name_plural }}
    from secondary_summary
)

-- =====================================================================
-- Final SELECT: one wide row per {{ ads_grain }}
-- =====================================================================

select
    -- FIXME(select-star): replace e.* with explicit enriched columns
    e.*,
    s.total_{{ entity_name_plural }},
    s.grand_total_{{ lifetime_measure }},
    s.avg_{{ entity_name }}_{{ lifetime_measure }},
    s.repeat_{{ entity_name_plural }}
from enriched e
cross join summary_stats s
