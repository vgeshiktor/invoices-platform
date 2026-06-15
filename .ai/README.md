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

## Guardrails

- Keep task packets short and anchored to real repo files.
- Reuse existing repo docs before adding new process.
- Record `TBD` instead of guessing.
- Do not add benchmark result rows until a real eval run happens.
