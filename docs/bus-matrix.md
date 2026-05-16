# Bus Matrix Design

The enterprise bus matrix is the foundational planning artifact in Kimball dimensional modeling. It maps business processes (rows) to the dimensions that describe them (columns), ensuring consistency across marts and enabling conformed analysis.

## Table of Contents

- [What Is a Bus Matrix](#what-is-a-bus-matrix)
- [How to Design One](#how-to-design-one)
- [Conformed Dimensions](#conformed-dimensions)
- [Role-Playing Dimensions](#role-playing-dimensions)
- [The Ecommerce Example](#the-ecommerce-example)
- [Multi-Mart Extension](#multi-mart-extension)
- [Maintaining the Matrix](#maintaining-the-matrix)

---

## What Is a Bus Matrix

A bus matrix is a grid where:
- **Rows** represent business processes (or fact tables, one per grain)
- **Columns** represent dimensions (descriptive context)
- **Cells** are marked when a business process is described by that dimension

The matrix serves three critical purposes:

1. **Scope planning** -- before writing any SQL, you know exactly which dimensions each fact table will reference
2. **Conformance enforcement** -- shared dimensions appear as columns used by multiple rows, making it obvious when two marts describe the same entity differently
3. **Prioritization** -- columns with the most marks deliver the most analytical cross-cutting value and should be built first

### Relationship to mart-forge Layers

In mart-forge terms:
- Each **row** corresponds to a DWD (fact) model
- Each **column** corresponds to a DIM model
- DWS models aggregate across the cells (a DWS references the same fact-dimension relationships as the DWD it aggregates)
- ADS models flatten the grid into a single wide table for a specific consumer

---

## How to Design One

### Step 1: Identify Business Processes

List the measurable events or transactions in your domain. Each becomes a candidate fact table.

Ask these questions:
- What events happen that the business wants to measure?
- What transactions get recorded?
- At what grain does each event occur?

**Common patterns:**

| Domain | Business Processes |
|--------|-------------------|
| E-commerce | Orders, Returns, Shipments, Page Views |
| SaaS | Subscriptions, Usage Events, Support Tickets |
| Finance | Trades, Settlements, Cash Flows |
| Healthcare | Encounters, Claims, Prescriptions |

### Step 2: Identify Dimensions

For each business process, ask: "By what attributes would analysts want to filter, group, or slice this data?"

Every business process typically has:
- **Who** -- customer, user, patient, trader
- **What** -- product, service, instrument, procedure
- **When** -- date/time (always present)
- **Where** -- location, store, region, exchange
- **Why/How** -- promotion, channel, method, status

### Step 3: Declare the Grain

Before filling in the matrix, write a grain statement for each business process. The grain is the most atomic level of detail captured by the fact table.

**Format:** "One row per {what} per {time period}"

Examples:
- "One row per order line item" (ecommerce orders)
- "One row per trade execution" (securities trading)
- "One row per patient encounter per day" (healthcare)

The grain determines which dimensions are applicable. If the grain is "per order line", then the product dimension applies (each line has one product). If the grain is "per order", then product does NOT apply at the fact level (an order can have many products).

### Step 4: Fill the Grid

Mark each cell where a dimension applies to a business process:

- **X** -- The dimension directly joins to the fact table via foreign key
- **R** -- Role-playing: the same dimension is used multiple times (e.g., date as order_date and ship_date)
- *(empty)* -- Not applicable at this grain

### Step 5: Identify Conformed Dimensions

Look for columns that span multiple rows. These are conformed dimensions -- they must use the same definition, the same surrogate keys, and the same attribute columns across all facts that reference them.

---

## Conformed Dimensions

A conformed dimension is a dimension table shared across multiple fact tables with identical structure, keys, and attribute values.

### Why Conformance Matters

Without conformed dimensions, you cannot drill across business processes. If `mart_A.dim_customer` and `mart_B.dim_customer` define "customer" differently (different keys, different attributes, different SCD handling), then a query joining the two marts will produce incorrect results.

### Rules for Conformance

1. **Same surrogate key generation** -- If `dim_customer` uses `customer_sk`, all fact tables that reference customers must use the same `customer_sk` values
2. **Same natural key** -- The business identifier (`customer_id`) must come from the same source system or be mapped through a master data management (MDM) process
3. **Same attributes** -- Core descriptive columns must match. A `dim_customer` that has `tier` in one mart but not another is not conformed
4. **Same SCD strategy** -- If `dim_customer` is SCD Type 2 in one mart, it must be SCD Type 2 everywhere

### In mart-forge

- Place shared dimensions in a central `dim/` directory
- Reference them via `{{ ref('prefix_dim_entity') }}` from all fact tables
- The `mart-review` skill checks that fact tables join to all dimensions declared in the bus matrix

---

## Role-Playing Dimensions

A role-playing dimension is a single physical dimension table used multiple times in the same fact table, each time playing a different role.

The most common example is the date dimension:

```sql
-- In the DWD fact table
left join dates as order_date_dim
    on fact.order_date = order_date_dim.full_date
left join dates as ship_date_dim
    on fact.ship_date = ship_date_dim.full_date
```

### In the Bus Matrix

Role-playing dimensions get an **R** mark and appear as separate columns:

| Process | Customer | Product | Date (order) | Date (ship) |
|---------|----------|---------|--------------|-------------|
| Orders  | X        | X       | R            | R           |

### In mart-forge

- Build one `dim_date` model
- In the DWD model, join to it once per role
- Foreign key columns differentiate the roles: `order_date_key`, `ship_date_key`
- In `schema.yml`, each FK gets its own `relationships` test pointing to `dim_date.date_key`

---

## The Ecommerce Example

The reference ecommerce mart (`examples/ecommerce-orders-mart/`) implements the following bus matrix:

### Dimensions

| Dimension | Model | SCD Type | Key Columns |
|-----------|-------|----------|-------------|
| Date | `ecom_dim_date` | Type 0 (static) | `date_key` (SK), `full_date` (NK) |
| Customer | `ecom_dim_customer` | Type 2 (history) | `customer_sk` (SK), `customer_id` (NK) |
| Product | `ecom_dim_product` | Type 1 (overwrite) | `product_sk` (SK), `product_id` (NK) |

### Bus Matrix Grid

```
                          | Date | Customer | Product |
                          |------|----------|---------|
Order Line Items (DWD)    |  X   |    X     |    X    |
Daily Revenue (DWS)       |  X   |    -     |    -    |
Customer Lifetime (DWS)   |  -   |    X     |    -    |
Product Trend (DWS)       |  X   |    -     |    X    |
Executive Dashboard (ADS) |  X   |    *     |    -    |
```

Legend: **X** = direct FK join, **-** = not applicable at this grain, **\*** = indirect (via DWS aggregation, not direct FK)

### How to Read This

- **Order Line Items** is the atomic fact table. It joins to all three dimensions via surrogate keys (`order_date_key`, `customer_sk`, `product_sk`).
- **Daily Revenue** aggregates orders to the day grain, so it only needs the date dimension.
- **Customer Lifetime** aggregates to the customer grain (to-date), so it only needs the customer dimension.
- **Product Trend** aggregates to the product-day grain, so it needs both date and product.
- **Executive Dashboard** is an ADS that combines daily revenue (which has date) with customer summary stats (aggregated, not a direct FK join).

### Observations

- **Date** is the most-used dimension (4 of 5 models) -- it should be built first
- **Customer** appears in 3 models -- conformed SCD Type 2 across all of them
- **Product** appears in 3 models -- conformed SCD Type 1

---

## Multi-Mart Extension

As your warehouse grows beyond a single mart, the bus matrix extends horizontally. Each new mart adds rows (business processes), and shared columns (conformed dimensions) connect them.

### Example: Adding a Returns Mart

```
                          | Date | Customer | Product | Return Reason |
                          |------|----------|---------|---------------|
Order Line Items          |  X   |    X     |    X    |      -        |
Return Line Items         |  X   |    X     |    X    |      X        |
Daily Revenue             |  X   |    -     |    -    |      -        |
Daily Returns             |  X   |    -     |    X    |      X        |
```

- **Date**, **Customer**, and **Product** are conformed across both marts
- **Return Reason** is a new dimension specific to the returns process
- Analysts can drill across orders and returns because the shared dimensions are identical

### Registering Conformed Dimensions

When you add a new mart, check the existing bus matrix for dimensions that already exist. If your mart needs `dim_customer`, use the existing one -- do not create a new version.

In `mart.yml`, reference conformed dimensions from a shared location:

```yaml
dimensions:
  conformed:
    - dim_date        # shared across all marts
    - dim_customer    # shared across orders + returns
  local:
    - dim_return_reason  # specific to this mart
```

---

## Maintaining the Matrix

### When to Update

- **New business process** -- add a row, mark which existing dimensions apply
- **New dimension** -- add a column, check which existing processes need it
- **New mart** -- extend the matrix, verify conformed dimensions match
- **Schema evolution** -- if a dimension gains new attributes, all fact tables benefit automatically (no matrix change needed)

### Storage

The bus matrix can live in several places:

1. **`schema.yml` descriptions** -- each model's description documents which dimensions it references. The `mart-review` skill extracts this.
2. **A standalone `bus_matrix.yml`** -- machine-readable for CI validation
3. **This documentation** -- human-readable reference

### Validation

The `mart-review` skill checks bus matrix coverage:
- Every FK in a DWD model must have a corresponding dimension in the bus matrix
- Every dimension marked in the bus matrix must have a `relationships` test in `schema.yml`
- Conformed dimensions must not be duplicated across marts

### Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| Fact table with no dimension joins | Unanalyzable data -- no "by X" possible | Add at minimum a date dimension |
| Duplicate dimensions across marts | Drill-across impossible, conflicting definitions | Extract to a shared conformed dimension |
| Dimension with no fact references | Orphan table consuming resources | Remove or document as future-use |
| Multi-grain fact table | Aggregation confusion, double-counting risk | Split into separate fact tables per grain |
| Missing date dimension | No time-series analysis possible | Always include `dim_date` |

---

## Checklist for New Marts

- [ ] Business processes identified and listed as rows
- [ ] Grain declared for each business process
- [ ] Dimensions identified as columns (Who, What, When, Where, Why)
- [ ] Conformed dimensions checked against existing marts
- [ ] Role-playing dimensions noted with R marks
- [ ] Bus matrix grid filled in and reviewed before writing any models
- [ ] Matrix documented in `schema.yml` descriptions or standalone file
