# schema-evolve

Handle source schema changes (new columns) through the Kimball layer stack.

## What it does

When a data source adds a new column:
1. Updates ODS model with the new column (explicit column list, no SELECT *)
2. Classifies column as business attribute or technical metadata
3. Propagates to DWD if business attribute
4. Adds appropriate tests (not_null, accepted_values, relationships, range)
5. Updates schema.yml documentation
6. Outputs diff and migration notes

## Trigger phrases

- "evolve schema for {mart} -- source added column {name}"
- "add column {name} to the {domain} mart"
- "source schema changed, propagate to warehouse"
- "new field appeared in the API response"

## Important constraints

- Schema evolution is **additive only** -- never removes columns
- Preserves idempotency (no current_timestamp() in logic)
- Maintains grain (new column must not change fact table grain)
- Every new column gets at minimum a not_null assessment

## Prerequisites

- An existing mart with ODS model(s)
- Knowledge of the new column's name, type, and semantic meaning

## References

- Naming conventions: `docs/naming-conventions.md`
- Dimensional lifecycle: `docs/dimensional-lifecycle.md`
