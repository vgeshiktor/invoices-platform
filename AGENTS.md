# Invoices Platform Agent Guide

## Purpose

Use this file for stable repo operating rules for AI-assisted work.
Use `PLANS.md` for current project state and progress notes.
Use `.ai/` for task-scoped packets and evaluation inputs/results when work is substantial.

## Source Of Truth Order

1. Active task packet in `.ai/tasks/` when one exists for the current change.
2. `README.md` for repo overview, supported surfaces, and quick-start workflow.
3. `docs/USAGE.md` for current command behavior and operational runbooks.
4. `Makefile`, `pytest.ini`, and `requirements.txt` for executable workflow, validation entry points, and Python dependencies.
5. Implemented code and tests under `apps/` and `tests/` for behavior details.
6. `docs/CONTRIBUTING.md`, `docs/ARCHITECTURE.md`, and `docs/ONBOARDING.md` only when they contain project-specific guidance; today they are placeholders.

## Working Rules

- Keep changes proportional to the repo’s current maturity; prefer small doc and workflow updates over new process layers.
- Anchor recommendations to the implemented surfaces in this repo: CLI workflows, report generation, local stack, docs, and validation.
- Do not invent product, auth, parser, or reporting behavior; mark unknowns as `TBD`.
- Prefer root-level validation first:
  - `make test`
  - `make lint`
  - targeted `pytest` when a change is docs-only or scoped to one workflow
- Preserve the split between current behavior and future scope already used in `README.md` and `docs/USAGE.md`.

## AI Context Budget

- Start with `README.md`, `docs/USAGE.md`, and the active task packet if present.
- Read `Makefile`, `pytest.ini`, and `requirements.txt` only when validation or workflow fit matters.
- Treat placeholder docs as low-priority context until they are expanded.
- Prefer changed files and task-relevant tests over broad repo reads.
- Maximum initial files for substantial work: 6, then expand only when the missing context is clear.

## `.ai/` Usage

- Create or update a task packet in `.ai/tasks/` for substantial multi-file work, reviews, or workflow changes.
- Use `.ai/task-packet-template.md` for new packets.
- Keep benchmark task definitions in `.ai/evals/tasks.yaml`.
- Record benchmark outcomes only after a real run in `.ai/evals/results.csv`; do not fabricate result rows.
