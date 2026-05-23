{{
  config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key=['pull_date', 'option_symbol'],
    pre_hook="{{ http_retry_config(var('provider_timeout_ms', 30000), var('provider_retries', 3)) }}"
  )
}}

{% if var('use_fixture', false) %}

SELECT pull_date, ticker, provider, pull_ts_utc, quote_ts_utc, run_id,
       option_symbol, bid, bid_size, ask, ask_size, iv, open_interest, volume,
       delta, gamma, theta, vega, rho, theo, change, opt_open, opt_high, opt_low,
       tick, last_trade_price, last_trade_time, percent_change, prev_day_close,
       expiry, option_type, strike, underlying_close, cboe_timestamp
FROM read_parquet('fixtures/gme_ods_cboe_options_chain.parquet')

{% else %}

WITH raw_unnested AS (
    SELECT
        unnest(data.options) AS elem,
        data.close AS underlying_close,
        "timestamp" AS cboe_timestamp
    FROM {{ http_read_json(var('provider_url'), var('provider_max_object_size', 10485760)) }}
)
SELECT
    CURRENT_DATE                                                      AS pull_date,
    'GME'                                                             AS ticker,
    'cboe'                                                            AS provider,
    CAST(cboe_timestamp AS TIMESTAMP)                                 AS pull_ts_utc,
    CAST(cboe_timestamp AS TIMESTAMP)                                 AS quote_ts_utc,
    '{{ var("run_id", "manual") }}'                                   AS run_id,

    elem['option']                                                    AS option_symbol,
    CAST(elem['bid'] AS DOUBLE)                                       AS bid,
    CAST(elem['bid_size'] AS INT)                                     AS bid_size,
    CAST(elem['ask'] AS DOUBLE)                                       AS ask,
    CAST(elem['ask_size'] AS INT)                                     AS ask_size,
    CAST(elem['iv'] AS DOUBLE)                                        AS iv,
    CAST(elem['open_interest'] AS INT)                                AS open_interest,
    CAST(elem['volume'] AS INT)                                       AS volume,
    CAST(elem['delta'] AS DOUBLE)                                     AS delta,
    CAST(elem['gamma'] AS DOUBLE)                                     AS gamma,
    CAST(elem['theta'] AS DOUBLE)                                     AS theta,
    CAST(elem['vega'] AS DOUBLE)                                      AS vega,
    CAST(elem['rho'] AS DOUBLE)                                       AS rho,
    CAST(elem['theo'] AS DOUBLE)                                      AS theo,
    CAST(elem['change'] AS DOUBLE)                                    AS change,
    CAST(elem['open'] AS DOUBLE)                                      AS opt_open,
    CAST(elem['high'] AS DOUBLE)                                      AS opt_high,
    CAST(elem['low'] AS DOUBLE)                                       AS opt_low,
    elem['tick']                                                      AS tick,
    CAST(elem['last_trade_price'] AS DOUBLE)                          AS last_trade_price,
    elem['last_trade_time']                                           AS last_trade_time,
    CAST(elem['percent_change'] AS DOUBLE)                            AS percent_change,
    CAST(elem['prev_day_close'] AS DOUBLE)                            AS prev_day_close,

    -- Right-anchored OCC parse: last 8 = strike, preceding 1 = C/P, preceding 6 = YYMMDD
    TRY_CAST(
        '20' || SUBSTRING(CAST(elem['option'] AS VARCHAR),
                           LENGTH(CAST(elem['option'] AS VARCHAR)) - 14, 2) || '-' ||
        SUBSTRING(CAST(elem['option'] AS VARCHAR),
                  LENGTH(CAST(elem['option'] AS VARCHAR)) - 12, 2) || '-' ||
        SUBSTRING(CAST(elem['option'] AS VARCHAR),
                  LENGTH(CAST(elem['option'] AS VARCHAR)) - 10, 2)
    AS DATE)                                                          AS expiry,
    CASE WHEN SUBSTRING(CAST(elem['option'] AS VARCHAR),
                        LENGTH(CAST(elem['option'] AS VARCHAR)) - 8, 1) = 'C'
         THEN 'call' ELSE 'put' END                                   AS option_type,
    TRY_CAST(RIGHT(CAST(elem['option'] AS VARCHAR), 8) AS DOUBLE)
        / 1000.0                                                      AS strike,

    underlying_close,
    cboe_timestamp

FROM raw_unnested
{% if is_incremental() and not var('backfill', false) %}
WHERE CURRENT_DATE >= (SELECT COALESCE(MAX(pull_date), DATE '1900-01-01') FROM {{ this }})
{% endif %}

{% endif %}
