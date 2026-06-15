# Invoices Platform Plans

## Current Repo State

- Purpose: support invoice discovery, PDF collection, monthly orchestration, and report generation across Gmail and Microsoft Graph.
- Stable orientation lives in `README.md` and `docs/USAGE.md`.
- Contributor/governance docs were previously missing or placeholder-level.

## Immediate Next Recommended Step

- No open non-review eval backlog remains. Treat the two review-oriented eval tasks as on-demand templates for future PR or workflow diffs, not standing milestones.

## Open TBDs

- None currently.

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
