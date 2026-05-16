# Agent Orchestration

<!-- Multi-agent workflow for mart scaffolding and review. -->

## Roles

### Builder Agent
Scaffolds the mart from `mart.yml` config using templates and Claude Code skills.

### Reviewer Agent
Audits the scaffolded mart against methodology rules. Produces enforceable gate artifacts.

## Workflow

1. User provides `mart.yml` with domain config
2. Builder agent runs `mart-bootstrap` skill → scaffolded dbt project
3. Builder agent runs `dqc-audit` skill → DQC scorecard
4. Reviewer agent runs `mart-review` skill → audit report with pass/fail gates
5. If gates fail, builder iterates; if gates pass, mart is ready for deployment
