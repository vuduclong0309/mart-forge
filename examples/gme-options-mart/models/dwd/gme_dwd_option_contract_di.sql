SELECT
    ods.pull_date,
    ods.ticker,
    ods.expiry,
    ods.strike,
    ods.option_type,
    ods.option_symbol,

    ods.bid,
    ods.ask,
    CASE WHEN ods.bid > 0 AND ods.ask > 0
         THEN (ods.bid + ods.ask) / 2.0
         ELSE ods.last_trade_price
    END                                                AS mid_price,
    ods.last_trade_price,

    COALESCE(ods.volume, 0)                            AS volume,
    COALESCE(ods.open_interest, 0)                     AS open_interest,

    ods.iv                                             AS implied_vol,
    ods.delta,
    ods.gamma,
    ods.theta,
    ods.vega,
    ods.rho,
    ods.theo,

    (ods.expiry - ods.pull_date)                       AS dte,
    ods.underlying_close                               AS spot,

    -- GEX contribution: gamma * OI * 100 * spot^2 * 0.01 * sign
    COALESCE(ods.gamma, 0)
        * COALESCE(ods.open_interest, 0)
        * 100
        * POWER(ods.underlying_close, 2)
        * 0.01
        * CASE WHEN ods.option_type = 'call' THEN 1 ELSE -1 END
                                                       AS gex_contribution,

    CASE
        WHEN (ods.expiry - ods.pull_date) > 365 THEN 'LEAP'
        WHEN (ods.expiry - ods.pull_date) <= 7  THEN 'WEEKLY'
        ELSE 'MONTHLY'
    END                                                AS series_type,

    ods.provider,
    ods.pull_ts_utc,
    ods.cboe_timestamp

FROM {{ ref('gme_ods_cboe_options_chain') }} ods
WHERE ods.open_interest > 0
  AND ods.strike IS NOT NULL
  AND (ods.expiry - ods.pull_date) >= 7
