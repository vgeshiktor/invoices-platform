# `.ai/` Contract

`.ai/` is the task-scoped companion to the repo-level guidance in `AGENTS.md`.

## How It Fits

- `AGENTS.md`: stable operating rules for AI-assisted work in this repo.
- `PLANS.md`: current repo state, progress notes, and the next recommended step.
- `README.md` and `docs/USAGE.md`: product and workflow source of truth.
- `.ai/tasks/`: task packets for substantial work.
- `.ai/evals/tasks.yaml`: representative benchmark task definitions for this repo.
- `.ai/evals/results.csv`: real benchmark outcomes only after execution.

## When To Use `.ai/`

- Use a task packet for substantial multi-file changes, workflow reviews, or validation-heavy work.
- Skip task-packet overhead for tiny, single-file, low-risk edits unless the user asks for one.

## Harness Map

- Instructions and guardrails: `AGENTS.md`
- Current-state memory: `PLANS.md`
- Task memory and spec: `.ai/tasks/`
- Eval contracts: `.ai/evals/tasks.yaml`
- Validation tools and contract checks: `Makefile` and `tests/`

## Lean-ctx-First Workflow

- Follow `AGENTS.md` as the canonical lean-ctx policy for substantial AI-assisted work.
- Start with `ctx_overview`, then use `ctx_tree` plus `ctx_search` before broad reads.
- Use `ctx_read` or `ctx_multi_read` for repo file access.
- Route tests, builds, `git`, and log-heavy commands through `ctx_shell` or `lean-ctx -c "<command>"`.
- If raw/native access is necessary, record the reason in the task packet instead of silently bypassing lean-ctx.
- If a dashboard command such as `lean-ctx gain --deep` fails, keep the normal `ctx_*` workflow and treat the failure as an upstream tooling issue unless repo work is blocked.

## Guardrails

- Keep task packets short and anchored to real repo files.
- Reuse existing repo docs before adding new process.
- Record `TBD` instead of guessing.
- Do not add benchmark result rows until a real eval run happens.
