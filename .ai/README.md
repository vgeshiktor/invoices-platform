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

## Interoperability Review Gate

- Record the integration mode: `tool | collaborator-agent | ui-contract | commerce-deferred`.
- Record the trust level: `official | internal | third-party-vetted | public-prototype-only`.
- Record the data scope: `synthetic | sanitized | real-nonprod | real-prod-readonly`.
- Prefer consuming an existing vetted tool, server, or skill before inventing custom wrappers.
- Keep real-data external access in non-production or sanitized environments by default, and require read-only scope when possible.
- Define the HITL approval point before side-effectful or sensitive external actions.
- Use declarative or trusted-catalog UI contracts for generated UI work; do not treat arbitrary executable UI as acceptable output.
- Keep AP2/UCP-style payment or procurement work in `commerce-deferred` until the repo has an explicit transaction surface and dedicated safeguards.

## Skill Governance Review Gate

- For skill-related work, use the existing task-packet fields rather than adding a skill-specific template.
- Treat external-skill adoption work like dependency review: record source, pinned version, trust level, data scope, HITL approval point, and validation expectations.
- Treat future repo-local skill authoring work as governed workflow design: record intended trigger surface, non-goals, helper assets/scripts, and portability assumptions in the same packet structure.
- For production/shared skill work, `Success criteria / eval rubric` and `Required validation` should cover `trigger`, `execution`, `regression`, and `token budget`.
- Keep skill governance proportional to current repo maturity: document and test the rules now, and defer runtime enforcement until the repo has an actual local skill library to govern.

## Security and Evaluation Review Gate

- Use `Trust level`, `Data scope`, `HITL approval point`, and `Write permission / read-only expectation` to encode the security posture for agentic work.
- Use `Success criteria / eval rubric` and `Required validation` to encode the evaluation posture for agentic work.
- For production/shared agent work, review the seven evaluation dimensions explicitly: intent satisfaction, functional correctness, visual and behavioral correctness, cost and efficiency, code quality and convention matching, trajectory quality, and self-repair behavior.
- For this repo's current maturity, allowed evaluation method mix is automated functional testing, security/safety review, human review, and browser-based testing when UI changes exist.
- Treat trace-level observability and internal-reasoning inspection as deferred prerequisites for richer glass-box evaluation, not current repo requirements.

## Guardrails

- Keep task packets short and anchored to real repo files.
- Reuse existing repo docs before adding new process.
- Record `TBD` instead of guessing.
- Do not add benchmark result rows until a real eval run happens.
