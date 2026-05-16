with source as (
    select
        customer_id,
        customer_name,
        email,
        city,
        state,
        tier,
        effective_date
    from {{ ref('ecom_ods_raw_customers') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by customer_id order by effective_date
        ) as rn,
        lead(effective_date) over (
            partition by customer_id order by effective_date
        ) as next_effective_date
    from source
),

scd2 as (
    select
        row_number() over (order by customer_id, effective_date) as customer_sk,
        customer_id,
        customer_name,
        email,
        city,
        state,
        tier,
        effective_date as effective_from,
        coalesce(
            next_effective_date - interval '1 day',
            date '2099-12-31'
        )::date as effective_to,
        case
            when next_effective_date is null then true
            else false
        end as is_current
    from ranked
),

unknown_member as (
    select
        -1 as customer_sk,
        'UNKNOWN' as customer_id,
        'Unknown' as customer_name,
        'unknown@unknown.com' as email,
        'Unknown' as city,
        'Unknown' as state,
        'Unknown' as tier,
        date '1900-01-01' as effective_from,
        date '2099-12-31' as effective_to,
        true as is_current
)

select * from scd2
union all
select * from unknown_member
