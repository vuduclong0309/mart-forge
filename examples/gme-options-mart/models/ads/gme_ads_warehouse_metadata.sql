{{
  config(
    materialized='table'
  )
}}

SELECT
    {% if var('use_fixture', false) %}
    'fixture'                                                             AS source_mode,
    'Fixture / Illustrative Data'                                         AS primary_source_label,
    CAST(NULL AS VARCHAR)                                                 AS primary_source_url,
    {% else %}
    'live'                                                                AS source_mode,
    'CBOE Delayed Quotes (15-min lag)'                                    AS primary_source_label,
    '{{ var("provider_url") }}'                                           AS primary_source_url,
    {% endif %}
    (SELECT MAX(pull_date) FROM {{ ref('gme_ods_cboe_options_chain') }})  AS data_as_of_date,
    (SELECT MAX(pull_ts_utc) FROM {{ ref('gme_ods_cboe_options_chain') }}) AS warehouse_built_at_utc
