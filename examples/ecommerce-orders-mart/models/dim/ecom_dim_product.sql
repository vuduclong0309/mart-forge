with source as (
    select
        product_id,
        product_name,
        category,
        subcategory,
        unit_price,
        supplier
    from {{ ref('ecom_ods_raw_products') }}
),

with_sk as (
    select
        row_number() over (order by product_id) as product_sk,
        product_id,
        product_name,
        category,
        subcategory,
        unit_price,
        supplier
    from source
),

unknown_member as (
    select
        -1 as product_sk,
        'UNKNOWN' as product_id,
        'Unknown' as product_name,
        'Unknown' as category,
        'Unknown' as subcategory,
        0.0 as unit_price,
        'Unknown' as supplier
)

select * from with_sk
union all
select * from unknown_member
