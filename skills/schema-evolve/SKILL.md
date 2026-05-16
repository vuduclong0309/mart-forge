---
name: schema-evolve
description: |
  Handle source schema changes for a Kimball mart. Adds new columns to ODS, propagates business attributes to DWD, adds appropriate tests, and updates schema.yml documentation. Produces a diff and migration notes.

  **Use when:**
  - "evolve schema for {mart} -- source added column {name}"
  - "add column {name} to the {domain} mart"
  - "source schema changed, propagate to warehouse"
  - "new field appeared in the API response"
  - A provider adds or renames columns in source data

  **Not for:**
  - Removing columns (requires manual review -- breaking change)
  - Adding entirely new source tables (use mart-bootstrap for new entities)
  - Changing grain or adding new fact tables (architectural change, not schema evolution)
  - Fixing broken tests (investigate root cause instead)
---

# Schema Evolve

Handles source column additions through the Kimball layer stack. Updates ODS with the new column (explicit column list), decides whether to propagate to DWD (business attribute) or stop at ODS (technical/metadata attribute), adds tests, and updates schema.yml.

## Constraints (read before doing anything)

- **ODS uses explicit column lists** -- no `SELECT *` ever. This is the schema drift detection mechanism. A new column MUST be explicitly added to the ODS SELECT clause.
- **Propagation decision is human-confirmable** -- if unsure whether a column is a business attribute (propagate to DWD) or technical metadata (stay in ODS), ASK. Default: propagate if it could appear in a WHERE/GROUP BY downstream.
- **Never remove columns** -- schema evolution is additive only. Removal requires a separate migration with deprecation period. If the user asks to remove, warn and confirm.
- **Test coverage is mandatory** -- every new column gets at minimum a `not_null` assessment (test if appropriate, or document as nullable in schema.yml). Business-critical columns get `accepted_values` or range tests.
- **Provenance columns are immutable** -- `provider`, `pull_ts_utc`, `quote_ts_utc`, `run_id` are never modified by schema evolution. They were set at mart creation.

## Workflow

1. **Identify the target mart and column** -> verify: confirm mart exists, find the ODS model that ingests from the affected source
   - Read `mart.yml` to get prefix and source configuration
   - Identify which ODS model corresponds to the source with the new column
   - Confirm the column doesn't already exist (grep for column name in models/)

2. **Update ODS model** -> verify: column added to explicit SELECT list with correct type/alias
   - Add column to the SELECT clause in the ODS `.sql` file
   - Position: after existing source columns, before provenance columns
   - Use appropriate alias if source naming differs from warehouse convention (snake_case)
   - If column has a source-side default or transformation, apply it here

3. **Decide propagation** -> verify: classify column and confirm with user if ambiguous

   Propagation rules:
   | Column Type | Propagate to DWD? | Examples |
   |-------------|-------------------|---------|
   | Business attribute | YES | strike_price, volume, status, category |
   | Derived metric input | YES | raw values needed for DWS calculations |
   | Technical metadata | NO (stays in ODS) | api_version, response_code, raw_json |
   | Audit/system field | NO | created_at from source, internal IDs |
   | FK to new dimension | YES + may need new DIM | category_id, region_code |

4. **Update DWD model (if propagating)** -> verify: column in SELECT, joins/transforms correct
   - Add column to DWD SELECT clause
   - If column is a FK to a new dimension, add the JOIN (or flag that a new DIM is needed)
   - Maintain grain -- new column must not change the fact table grain
   - No `current_timestamp()` -- preserve idempotency

5. **Update DWS/ADS (if aggregatable)** -> verify: only if the new column feeds an aggregation or appears in a consumer-facing OBT
   - If the column should appear in a DWS aggregation (e.g., new metric to sum/avg), update DWS
   - If the column should appear in the ADS one-big-table, add it there
   - Most schema evolutions stop at DWD -- DWS/ADS updates are optional

6. **Add tests** -> verify: at minimum one test per new column, appropriate to its type

   Test selection guide:
   | Column Characteristic | Test(s) to Add |
   |----------------------|----------------|
   | Primary key component | `not_null` + `unique` (or composite unique) |
   | Foreign key | `relationships` to target DIM |
   | Enum/categorical | `accepted_values` with known values |
   | Numeric metric | Range test (singular): min/max plausible bounds |
   | Required field | `not_null` |
   | Nullable field | Document as nullable in schema.yml description |
   | Date/timestamp | Format test or range test (not in future) |

7. **Update schema.yml** -> verify: new column documented with description, tests declared
   - Add column entry under the appropriate model in schema.yml
   - Include: name, description, tests
   - If column changes the model's grain or semantics, update the model description

8. **Generate migration notes** -> verify: output includes diff summary and any follow-up actions

## Output Checklist

- [ ] ODS model updated with new column in explicit SELECT list
- [ ] Propagation decision documented (business attr -> DWD, or stays in ODS)
- [ ] DWD model updated (if propagating)
- [ ] DWS/ADS updated (if applicable)
- [ ] At least one test added for the new column
- [ ] schema.yml updated with column documentation
- [ ] No `SELECT *` introduced
- [ ] No `current_timestamp()` introduced
- [ ] Grain unchanged (or explicitly noted if grain changes)
- [ ] Idempotency preserved (re-run produces same output)

## Output Format

```
## Schema Evolution -- {mart_name}

### Change
- Source: {source_name}
- New column: `{column_name}` ({type})
- Classification: {business_attribute|technical_metadata|fk_reference}

### Propagation
- ODS: UPDATED -- {model_name}
- DWD: {UPDATED|SKIPPED} -- {reason}
- DWS: {UPDATED|SKIPPED} -- {reason}
- ADS: {UPDATED|SKIPPED} -- {reason}

### Tests Added
- {test_type} on {model}.{column}
...

### Files Modified
- `models/ods/{file}.sql` -- added column to SELECT
- `models/dwd/{file}.sql` -- added column (if propagated)
- `schema.yml` -- column documentation + tests
...

### Follow-up Actions (if any)
- [ ] New DIM needed for {column} FK target
- [ ] DWS aggregation may want to include {column}
- [ ] Backfill needed for historical data (column will be NULL for old rows)
```

## Resources

- `docs/naming-conventions.md` -- Layer naming and column conventions
- `docs/dimensional-lifecycle.md` -- SCD types and idempotency contract
- Target mart's `models/ods/` -- current explicit column lists
- Target mart's `schema.yml` -- existing documentation and tests
