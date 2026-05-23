WITH contracts AS (
    SELECT pull_date, ticker, expiry, strike, option_type, open_interest, contract_class
    FROM {{ ref('gme_dwd_option_contract_di') }}
),

candidates AS (
    SELECT DISTINCT pull_date, ticker, expiry, contract_class, strike AS candidate
    FROM contracts
),

pain_calc AS (
    SELECT
        c.pull_date,
        c.ticker,
        c.expiry,
        c.contract_class,
        c.candidate,
        SUM(CASE
            WHEN ct.option_type = 'call' AND ct.strike < c.candidate
            THEN (c.candidate - ct.strike) * ct.open_interest * 100
            WHEN ct.option_type = 'put' AND ct.strike > c.candidate
            THEN (ct.strike - c.candidate) * ct.open_interest * 100
            ELSE 0
        END) AS total_pain
    FROM candidates c
    INNER JOIN contracts ct
        ON c.pull_date = ct.pull_date
        AND c.ticker = ct.ticker
        AND c.expiry = ct.expiry
        AND c.contract_class = ct.contract_class
    GROUP BY c.pull_date, c.ticker, c.expiry, c.contract_class, c.candidate
)

SELECT
    pull_date,
    ticker,
    expiry,
    contract_class,
    candidate AS max_pain_strike,
    total_pain AS min_total_pain
FROM pain_calc
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY pull_date, ticker, expiry, contract_class
    ORDER BY total_pain ASC
) = 1
