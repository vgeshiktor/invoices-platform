# Invoices Platform Plans

## Current Repo State

- Purpose: support invoice discovery, PDF collection, monthly orchestration, and report generation across Gmail and Microsoft Graph.
- Stable orientation lives in `README.md` and `docs/USAGE.md`.
- Contributor/governance docs were previously missing or placeholder-level.
- Live GitHub milestones `Week 1` through `Week 10` are now treated as the authoritative SaaS/control-plane backlog.
- The checked-in repo still reflects the earlier CLI/reporting baseline and does not yet contain the planned frontend workspace or control-plane APIs.

## Immediate Next Recommended Step

- Implement the roadmap baseline for Weeks 1-10:
  - recover the GitHub issue spec into repo docs
  - expand the OpenAPI contract
  - add `apps/web`
  - replace the Go `/healthz` stub with a control-plane API baseline

## Open TBDs

- Persistence/storage backend for the new control-plane surfaces beyond the initial in-memory baseline.
- Runtime strategy for long-running collection/report jobs in non-dev deployments.

## Progress Update

- `2026-06-11`: added a minimal AI workflow governance baseline:
  - root `AGENTS.md` for stable operating rules
  - root `PLANS.md` for current state and progress tracking
  - `.ai/` contract with task-packet template and benchmark seed files
- `2026-06-11`: completed the first real governance follow-through for `auth-token-flow-review`:
  - created `.ai/tasks/2026-06-11-auth-token-flow-review.md`
  - verified auth/token guidance against `docs/USAGE.md`, `Makefile`, `graph_invoice_finder.py`, and `tests/test_graph_invoice_auth.py`
  - recorded the first real benchmark result in `.ai/evals/results.csv`
- `2026-06-11`: completed the first real report-validation follow-through for `report-validation-surface-review`:
  - created `.ai/tasks/2026-06-11-report-validation-surface-review.md`
  - verified report output guidance against `README.md`, `docs/USAGE.md`, `Makefile`, `invoices_report.py`, and the report test suites
  - recorded the benchmark result in `.ai/evals/results.csv`
- `2026-06-11`: decided to keep `docs/CONTRIBUTING.md`, `docs/ARCHITECTURE.md`, and `docs/ONBOARDING.md` as placeholders until there is repo-specific guidance worth documenting, rather than inventing process or architecture detail.
- `2026-06-13`: closed the remaining non-review eval backlog:
  - executed `readme-governance-discovery`, `docs-usage-report-example`, `cli-monthly-runbook-check`, `local-stack-docs-fit`, and `command-surface-governance-pass`
  - aligned local-stack guidance with actual `make dev` / `make up` / `make down` / `make run-n8n` behavior
  - corrected the root env example to use the implemented `GRAPH_CLIENT_ID` variable name
  - kept review-oriented eval tasks as invocation-only templates rather than treating them as open milestones
- `2026-06-18`: hardened lean-ctx governance after observing strong `ctx_read` adoption but weaker shell-routing discipline:
  - updated `AGENTS.md` and `.ai/README.md` to make lean-ctx-first routing explicit for substantial repo work
  - expanded `.ai/task-packet-template.md` with overview, search, and compressed-shell planning checkpoints
  - added a reusable eval template plus contract-test coverage so the lean-ctx workflow remains discoverable and hard to regress
- `2026-06-18`: aligned repo governance with the Day 1 agentic-engineering guidance at the workflow layer:
  - treated `AGENTS.md`, `.ai/tasks/`, `.ai/evals/tasks.yaml`, and repo contract tests as maintained governance assets
  - added explicit prototype vs production planning fields plus AI-specific review expectations for substantial work
  - normalized review templates with structured rubric and ship-gate metadata
  - intentionally deferred deeper runtime observability, traces, and model-routing work until the repo needs more than governance hardening
- `2026-06-19`: reconciled repo planning with the live GitHub roadmap:
  - validated that Milestones `Week 1` through `Week 10` remain open in GitHub
  - confirmed the repo lacks the referenced frontend/control-plane implementation surfaces
  - promoted the GitHub milestone backlog into the repo implementation baseline for the next phase of work
- `2026-06-21`: aligned repo governance with the Day 2 interoperability guidance at the workflow layer:
  - added repo-level defaults for tool vs collaborator-agent vs UI-contract decisions
  - expanded `.ai` task-packet and eval-review fields with trust level, data scope, HITL, and read-only expectations
  - added contract-test coverage so interoperability guardrails remain discoverable and hard to drift
  - explicitly deferred AP2/UCP-style commerce flows until the repo has a real autonomous transaction surface
- `2026-06-25`: aligned repo governance with the Day 3 skill-governance guidance at the workflow layer:
  - added repo-level defaults that distinguish `AGENTS.md`, Skills, and tools/MCP surfaces
  - documented source-selection, pinning, progressive-disclosure, portability, and eval-coverage expectations for future skill work
  - added a new day-3 governance task packet plus eval-catalog and contract-test coverage
  - intentionally deferred repo-local skill creation, runtime enforcement, telemetry, and CI-driven skill execution until the repo has a real skill library to govern
---
