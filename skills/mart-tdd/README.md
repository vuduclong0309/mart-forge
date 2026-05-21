# mart-tdd

Generate a Tech Design Document (TDD) with column-level calculation specs for a mart.

## What it does

Reads an approved `sign-off-prd.md` and `mart.yml` to produce a TDD with:
- Kimball 4-step design reasoning (business process, grain, dimensions, facts)
- Bus matrix cross-reference
- Source-to-target mapping across all layers (ODS through ADS)
- Physical table schemas with exact SQL expressions for every column
- DQC plan with control coverage matrix and test specifications
- Refresh and monitoring strategy
- Bidirectional traceability matrix (TDD field <-> SQL model + line number)

## Phase B gate

The TDD is the **Phase B gate** artifact. `mart-bootstrap` must not generate any model code until the TDD is signed off. This ensures every column has a specified calculation before code is written.

Gate sequence:
1. Phase A: `sign-off-prd.md` approved (business requirements)
2. **Phase B: `tech-design-doc.md` approved (physical design)**
3. Code generation: `mart-bootstrap` scaffolds dbt models from the approved TDD

## Trigger phrases

- "create a tech design for {mart}"
- "write TDD for {mart}"
- "design the physical schema for {mart}"

## Prerequisites

- A valid `mart.yml` config file
- An approved `sign-off-prd.md` (Phase A complete)
- Source system schema known (from provider docs or sample pull)

## References

- TDD template: `templates/tech-design-doc.template.md`
- Naming conventions: `docs/naming-conventions.md`
- DQC control catalog: `docs/dqc-framework.md`
- Bus matrix design: `docs/bus-matrix.md`
- Reference example: `examples/gme-options-mart/sign-off-prd.md` (includes completed calc specs)
