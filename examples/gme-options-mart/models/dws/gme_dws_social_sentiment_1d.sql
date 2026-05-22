SELECT
    observed_date AS pull_date,
    ticker,
    SUM(mention_count)                                     AS social_mention_count,
    ROUND(SUM(sentiment_score * mention_count)
          / NULLIF(SUM(mention_count), 0), 4)              AS social_sentiment_score
FROM {{ ref('gme_social_sentiment') }}
GROUP BY observed_date, ticker
