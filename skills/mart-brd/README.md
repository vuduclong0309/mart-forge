# mart-brd

Produce a Business Requirements Document (BRD) for a new Kimball mart — Phase A of the mart lifecycle.

## What it does

Reads client input (case study, data file, verbal description, existing docs) and generates a structured BRD covering:
- Business process identification and scope boundaries
- Metrics catalog with business definitions, units, and aggregation methods
- Domain glossary resolving ambiguous terminology
- Data source inventory with provenance tags
- Stakeholder personas and acceptance criteria
- Cadence, SLA, and lifecycle expectations

## Hard gate

**No TDD (Phase B) until the BRD is signed off.** The skill stops after producing the BRD and waits for operator approval before any technical design begins.

## Trigger phrases

- "create a BRD for {domain/source}"
- "write business requirements for a new mart"
- "Phase A for {domain}"
- "what metrics should this mart have?"

## Prerequisites

- At least one form of client input (case study, sample data, description, or existing docs)
- No technical prerequisites — the BRD is a business document

## References

- BRD template: `templates/business-requirements.template.md`
- Lifecycle phases: `docs/agent-orchestration.md`
- Bus matrix patterns: `docs/bus-matrix.md`
