-- DQC Control: Duplicate Detection
-- Verifies no duplicate business keys exist in the fact table grain.
select
    order_id,
    line_id,
    count(*) as row_count
from {{ ref('ecom_dwd_order_line_di') }}
group by order_id, line_id
having count(*) > 1
