select
    date_key,
    full_date,
    year,
    quarter,
    month,
    month_name,
    day_of_week,
    day_name,
    is_weekend,
    is_holiday
from {{ ref('dim_date') }}
