{{
  config(
    materialized='table'
  )
}}

WITH raw_unnested AS (
    SELECT
        unnest(data.options) AS elem,
        data.close AS underlying_close,
        "timestamp" AS cboe_timestamp
    FROM read_json_auto(
        'https://cdn.cboe.com/api/global/delayed_quotes/options/GME.json',
        maximum_object_size=10485760
    )
)
SELECT
    CURRENT_DATE                                                      AS pull_date,
    'GME'                                                             AS ticker,
    'cboe'                                                            AS provider,
    NOW()                                                             AS pull_ts_utc,
    cboe_timestamp                                                    AS quote_ts_utc,
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

    -- Parsed from OCC symbol: {TICKER}{YYMMDD}{C/P}{8-digit strike}
    TRY_CAST(
        '20' || SUBSTRING(CAST(elem['option'] AS VARCHAR), 4, 2) || '-' ||
        SUBSTRING(CAST(elem['option'] AS VARCHAR), 6, 2) || '-' ||
        SUBSTRING(CAST(elem['option'] AS VARCHAR), 8, 2)
    AS DATE)                                                          AS expiry,
    CASE WHEN SUBSTRING(CAST(elem['option'] AS VARCHAR), 10, 1) = 'C'
         THEN 'call' ELSE 'put' END                                   AS option_type,
    TRY_CAST(SUBSTRING(CAST(elem['option'] AS VARCHAR), 11) AS DOUBLE)
        / 1000.0                                                      AS strike,

    underlying_close,
    cboe_timestamp

FROM raw_unnested
