# Dimensional Lifecycle

Dimensions in a Kimball warehouse are not static. They change over time as business attributes evolve, new members arrive, and late data shows up. This guide covers surrogate keys, natural keys, unknown members, SCD types, and late-arriving data handling.

## Table of Contents

- [Keys: Surrogate vs Natural](#keys-surrogate-vs-natural)
- [Unknown Members](#unknown-members)
- [SCD Type 0: Fixed Attributes](#scd-type-0-fixed-attributes)
- [SCD Type 1: Overwrite](#scd-type-1-overwrite)
- [SCD Type 2: History Tracking](#scd-type-2-history-tracking)
- [Hybrid SCD Strategies](#hybrid-scd-strategies)
- [Late-Arriving Data](#late-arriving-data)
- [Implementation in mart-forge](#implementation-in-mart-forge)

---

## Keys: Surrogate vs Natural

### Natural Keys

A natural key is the business identifier from the source system. It is meaningful to humans and exists in the operational database.

Examples:
- `customer_id` = "C-10042" (from the CRM)
- `product_id` = "SKU-A100" (from the catalog)
- `order_id` = "ORD-2026-05-001" (from the order system)

Natural keys are:
- Human-readable and meaningful
- Subject to change (company mergers, system migrations, format changes)
- Not guaranteed unique across source systems
- Often strings (varchar), which are slower to join than integers

### Surrogate Keys

A surrogate key is a warehouse-generated integer with no business meaning. It exists only within the dimensional model.

Examples:
- `customer_sk` = 1, 2, 3, ... (auto-generated in the DIM model)
- `product_sk` = 1, 2, 3, ... (auto-generated in the DIM model)
- `date_key` = 20260516 (YYYYMMDD integer for dates)

Surrogate keys are:
- Integers -- fast to join and index
- Warehouse-controlled -- immune to source system changes
- Required for SCD Type 2 (one natural key maps to multiple surrogate keys)
- The column that fact tables reference via foreign key

### Why Both Are Needed

| Purpose | Use Natural Key | Use Surrogate Key |
|---------|-----------------|-------------------|
| Join fact to dimension | No | Yes |
| Look up a specific business entity | Yes | No |
| Handle SCD Type 2 (history) | Yes (partition by) | Yes (unique row ID) |
| Cross-system integration | Yes (with mapping table) | No |
| Performance (join speed) | Slower (varchar) | Faster (integer) |

### mart-forge Convention

```sql
-- In DIM model
row_number() over (order by customer_id, effective_date) as customer_sk,
customer_id,  -- natural key preserved alongside
...
```

- Surrogate key column: `{entity}_sk`
- Natural key column: `{entity}_id`
- Surrogate key is always the first column in the SELECT
- Both are `not_null`; surrogate key is `unique`

---

## Unknown Members

An unknown member is a special row in every dimension table with surrogate key = -1 and all attributes set to placeholder values. It exists to handle foreign key integrity when fact records reference dimension members that do not (yet) exist.

### Why Unknown Members Are Required

Without an unknown member, a fact table row that references a customer not yet in `dim_customer` has two options:

1. **NULL foreign key** -- breaks FK integrity tests and makes joins fail silently
2. **Inner join** -- drops the fact row entirely, losing data

Both are unacceptable. The unknown member provides a third option:

3. **Default to -1** -- the fact row joins to the unknown member, preserving data integrity while flagging the gap

### Implementation

Every DIM model must include an unknown member row via a `UNION ALL`:

```sql
-- From ecom_dim_customer.sql
with scd2 as (
    select
        row_number() over (...) as customer_sk,
        customer_id,
        customer_name,
        ...
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
```

### Unknown Member Rules

| Column Type | Unknown Value |
|-------------|---------------|
| Surrogate key | `-1` |
| Natural key | `'UNKNOWN'` |
| Varchar attributes | `'Unknown'` |
| Numeric attributes | `0` or `0.0` |
| Date (effective_from) | `'1900-01-01'` |
| Date (effective_to) | `'2099-12-31'` |
| Boolean (is_current) | `true` |
| Email | `'unknown@unknown.com'` |

### In Fact Tables

Fact table joins use `COALESCE` to default to the unknown member:

```sql
-- From ecom_dwd_order_line_di.sql
coalesce(c.customer_sk, -1) as customer_sk,
coalesce(p.product_sk, -1) as product_sk,
coalesce(d.date_key, -1) as order_date_key,
```

This ensures every fact row always has a valid FK, and the `relationships` test in `schema.yml` passes.

---

## SCD Type 0: Fixed Attributes

Type 0 means the dimension never changes after initial load. The original value is retained forever.

### When to Use

- Reference data that is definitionally static (e.g., calendar dates, country codes, currency codes)
- Attributes that must not change for audit or compliance reasons
- Historical snapshots that should reflect the original value

### Implementation

Type 0 dimensions are simply loaded once and never updated:

```sql
-- ecom_dim_date.sql -- Type 0 example
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
```

No SCD columns (`effective_from`, `effective_to`, `is_current`) are needed because the data does not change.

### In schema.yml

```yaml
- name: ecom_dim_date
  description: "Conformed date dimension (role-playing). Grain: one row per calendar day."
```

The absence of `effective_from`/`effective_to` implicitly signals Type 0.

---

## SCD Type 1: Overwrite

Type 1 means the old value is overwritten with the new value. No history is kept.

### When to Use

- Corrections to errors (misspelled names, wrong categories)
- Attributes where only the current value matters for analysis
- When storage and complexity savings outweigh the loss of history

### Implementation

The ecommerce mart's `ecom_dim_product` is a Type 1 example:

```sql
-- ecom_dim_product.sql -- Type 1
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
```

### Characteristics

- One row per natural key (no versioning)
- Surrogate key is stable (same `product_id` always gets the same `product_sk`)
- Simple to implement and query
- Historical queries reflect current attribute values, not the values at the time of the transaction

### Trade-off

If a product's category changes from "Electronics" to "Computers", all historical fact rows involving that product now show "Computers" -- even orders placed when it was categorized as "Electronics". If this matters, use Type 2.

---

## SCD Type 2: History Tracking

Type 2 creates a new row for every change, preserving the full history of attribute values.

### When to Use

- Customer tier changes (bronze -> silver -> gold) that affect analysis
- Pricing changes where historical pricing matters
- Any attribute where "what was the value at the time of the transaction?" is a valid question

### Implementation

The ecommerce mart's `ecom_dim_customer` is a Type 2 example:

```sql
-- ecom_dim_customer.sql -- Type 2
with source as (
    select customer_id, customer_name, email, city, state, tier, effective_date
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
)

select * from scd2
union all
select * from unknown_member
```

### Required Columns

| Column | Type | Description |
|--------|------|-------------|
| `{entity}_sk` | integer | Surrogate key -- unique per version |
| `{entity}_id` | varchar | Natural key -- same across versions |
| `effective_from` | date | Start of this version's validity |
| `effective_to` | date | End of this version's validity (`2099-12-31` for current) |
| `is_current` | boolean | `true` only for the latest version |

### How Fact Tables Join to SCD Type 2

The join must be date-aware to pick the correct version:

```sql
-- From ecom_dwd_order_line_di.sql
left join customers c
    on o.customer_id = c.customer_id
    and o.order_date >= c.effective_from
    and o.order_date <= c.effective_to
```

This ensures that an order placed on 2026-01-15 joins to the customer's attributes as they were on that date, not the current attributes.

### Querying SCD Type 2

```sql
-- Current attributes only (most common)
select * from ecom_dim_customer where is_current = true

-- Attributes at a specific point in time
select * from ecom_dim_customer
where '2026-03-15' between effective_from and effective_to

-- Full history for a customer
select * from ecom_dim_customer
where customer_id = 'C-10042'
order by effective_from
```

---

## Hybrid SCD Strategies

Real-world dimensions often combine SCD types within the same table:

| Attribute | SCD Type | Rationale |
|-----------|----------|-----------|
| customer_name | Type 1 | Name corrections should overwrite (no analytical value in old name) |
| email | Type 1 | Current email is all that matters |
| tier | Type 2 | Tier changes drive segmentation analysis |
| city, state | Type 2 | Location changes affect regional reporting |

### Implementation

In a hybrid approach, Type 1 attributes are updated in-place on the current row, while Type 2 attributes trigger a new row. The `effective_from`/`effective_to` columns track the Type 2 changes.

In mart-forge, the simplest approach is:
1. Model the dimension as Type 2 (new row on any tracked attribute change)
2. Source system provides effective dates for tracked changes
3. Type 1 attributes are simply included in every row -- they will reflect the latest value when the source is refreshed

---

## Late-Arriving Data

Late-arriving data occurs when a fact record arrives referencing a dimension member that is not yet in the dimension table, or when a dimension update arrives after fact records have already been loaded.

### Late-Arriving Facts

A fact row arrives, but the dimension member it references does not exist yet.

**Solution:** The `COALESCE(..., -1)` pattern handles this automatically:

```sql
coalesce(c.customer_sk, -1) as customer_sk
```

The fact row is loaded with `customer_sk = -1` (unknown member). When the dimension member eventually arrives, one of two approaches is used:

1. **Reprocess the fact table** -- On next full rebuild, the join succeeds and the unknown member reference is replaced with the correct surrogate key
2. **Leave as-is** -- Accept that early-arriving facts reference the unknown member until the next scheduled rebuild

### Late-Arriving Dimensions

A dimension attribute change is discovered after fact rows have already been loaded with the old attributes.

**For SCD Type 1:** No special handling needed. On next rebuild, the dimension table overwrites the old value, and fact table joins pick up the new attribute.

**For SCD Type 2:** A new version row must be inserted with the correct `effective_from` date. This may be backdated. Fact rows that fall within the new version's effective period will automatically join to it on next rebuild.

### mart-forge Approach

mart-forge defaults to **full table rebuilds** for DIM, DWS, and ADS layers (materialized as `table`, not `incremental`). This means:

- Late-arriving dimension data is handled automatically on next `dbt run`
- Late-arriving facts that referenced the unknown member get corrected on next rebuild
- Only DWD uses incremental materialization, and even there, idempotent `unique_key` dedup ensures reruns are safe

This trade-off favors correctness over processing speed. For very large fact tables where full rebuilds are impractical, configure DWD as incremental with a lookback window:

```sql
{% if is_incremental() %}
where quote_ts_utc > (select max(quote_ts_utc) - interval '3 days' from {{ this }})
{% endif %}
```

The 3-day lookback window catches most late-arriving facts while keeping processing efficient.

---

## Implementation in mart-forge

### Declaring SCD Type

In `schema.yml`, the model description should state the SCD type:

```yaml
- name: ecom_dim_customer
  description: >
    Customer dimension with SCD Type 2 history tracking tier changes.
    Grain: one row per customer per effective period.

- name: ecom_dim_product
  description: >
    Product dimension (SCD Type 1 -- overwrite on change).
    Grain: one row per product.

- name: ecom_dim_date
  description: >
    Conformed date dimension (role-playing).
    Grain: one row per calendar day.
```

### Tests for Dimension Integrity

```yaml
# SCD Type 2 tests
columns:
  - name: customer_sk
    tests:
      - not_null
      - unique        # Every version row has a unique SK
  - name: customer_id
    tests:
      - not_null       # Natural key is NOT unique (multiple versions per customer)
  - name: is_current
    tests:
      - not_null
  - name: effective_from
    tests:
      - not_null
  - name: effective_to
    tests:
      - not_null

# SCD Type 1 tests
columns:
  - name: product_sk
    tests:
      - not_null
      - unique
  - name: product_id
    tests:
      - not_null       # Natural key IS unique for Type 1 (one row per entity)
```

### Template Patterns

The `templates/models/dim/template.sql` file provides a starting point for both SCD types. Use the Type 2 template when history tracking is needed, and simplify to Type 1 by removing the ranking and effective date logic.

### Checklist

- [ ] Every DIM has a surrogate key (`{entity}_sk`) and natural key (`{entity}_id`)
- [ ] Every DIM includes an unknown member row (sk = -1)
- [ ] SCD type is declared in `schema.yml` description
- [ ] SCD Type 2 dims have `effective_from`, `effective_to`, `is_current`
- [ ] Fact table joins to SCD Type 2 dims use date-range predicates
- [ ] Fact table FKs default to -1 via `COALESCE` for missing dimension members
- [ ] DIM models are materialized as `table` (full rebuild) for correctness
- [ ] Late-arriving data strategy is documented per dimension
