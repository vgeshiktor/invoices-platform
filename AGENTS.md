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

## Agentic Engineering Defaults

- Substantial work requires a task packet in `.ai/tasks/`; keep tiny, single-file edits lightweight unless the user asks for the packet.
- Every new task packet must declare a working mode: `prototype` for exploration or `production` for changes intended to ship/shared workflows.
- Before implementation begins, shipping changes must define the required tests and, when the task behaves like an agent/workflow review, the success criteria or eval rubric.
- Review AI-generated code with equal or higher scrutiny than human-written code, especially around hallucinated dependencies, missing failure handling, and unsupported policy claims.
- When an agent repeats a mistake, convert the lesson into a repo rule, template field, example, or test instead of relying on memory alone.

## Interoperability Defaults

- Choose tools or MCP-style integrations for bounded, schema-driven, fire-and-forget operations.
- Choose collaborating agents or subagents for unbounded, ambiguous, multi-turn work that may pause for clarification.
- For new integrations, search for an existing vetted tool, server, or skill first before inventing custom wrappers.
- Prefer official, internal, or otherwise vetted registries over public community endpoints.
- Do not use public or unverified tool servers as production dependencies.
- Never place credentials in prompts or checked-in scripts; continue using environment variables or repo-approved secret configuration paths.
- Default sensitive or real-data external access to non-production or sanitized environments; if real data access is unavoidable, require read-only scope when possible.
- For side-effectful or sensitive external actions, require explicit human approval before side-effectful or sensitive external tool calls.
- For UI-generating work, allow declarative or trusted-catalog UI contracts rather than arbitrary generated executable UI.
- Defer AP2/UCP-style payment or procurement flows until the repo has an explicit autonomous transaction surface and dedicated guardrails.

## Skill Governance Defaults

- Treat `AGENTS.md` as always-loaded repo guidance, Skills as on-demand procedural runbooks, and tools/MCP servers as the execution surfaces those runbooks can call.
- Skills are for narrow, repeatable workflows. Always-on project conventions belong in `AGENTS.md`, not in a skill body.
- For adoption, prefer first-party, internal, or otherwise vetted skills first. Pin adopted skills to a reviewed version or commit, review them like code, and do not use public or unverified skills as production dependencies.
- Future repo-local skills should follow one skill, one job. If a workflow cannot be described in one sentence, split it before writing `SKILL.md`.
- The description field is the routing interface and must state what it does, when to use it, and when not to use it.
- Use progressive disclosure for long or edge-case material by moving it into `references/`, and keep deterministic helper logic in `scripts/` when the agent would otherwise keep re-deriving it.
- Do not hard-code secrets, credentials, or machine-specific paths. Repo-local skills should stay portable across compliant runtimes.
- For sensitive, side-effectful, or real-data work, skill usage inherits the existing HITL, read-only, and sanitized data expectations from this repo's interoperability and security guidance.

## Agent Security and Evaluation Defaults

- generated code, generated dependencies, and new tools are untrusted until verified; check them against repo policy, tests, and security guidance before shared use
- Prefer vetted registries, explicit pinning, and review-before-adoption for packages, tools, and generated integrations to reduce hallucinated-package and slopsquatting risk.
- Keep external access non-interactive and governed. Do not let autonomous workflows browse or fetch arbitrary public resources outside documented repo workflows and approved access paths.
- keep permissions narrow, default sensitive work to read-only or non-production scopes, and require human approval for high-risk or irreversible actions
- require small, reviewable change batches so failures stay inspectable and rollback remains tractable
- Reject success claims that depend on deleting, weakening, or mocking tests instead of fixing the underlying behavior.
- Distinguish safety/security from shipping quality: staying inside the boundary is not enough to claim success if intent, correctness, or repo conventions drift.

## AI Context Budget

- Start with `README.md`, `docs/USAGE.md`, and the active task packet if present.
- Read `Makefile`, `pytest.ini`, and `requirements.txt` only when validation or workflow fit matters.
- Treat placeholder docs as low-priority context until they are expanded.
- Prefer changed files and task-relevant tests over broad repo reads.
- Maximum initial files for substantial work: 6, then expand only when the missing context is clear.

## Lean-ctx Workflow

- For every substantial repository task, start with `ctx_overview` using the current task description.
- Use `ctx_tree` to confirm repo structure before broad exploration.
- Use `ctx_search` before broad reads, then use `ctx_read` or `ctx_multi_read` for file access.
- Route tests, builds, `git`, logs, and other output-heavy commands through `ctx_shell` or `lean-ctx -c "<command>"`.
- Use raw or native shell/file reads only when exact uncompressed output is required or lean-ctx is unavailable.
- If a lean-ctx dashboard or observability command fails, treat it as an upstream tooling issue rather than a repo-policy exception.
- If compression hooks need to be bypassed temporarily for debugging, use `lean-ctx-off`, then return to the lean-ctx-first workflow for normal repo tasks.

## `.ai/` Usage

- Create or update a task packet in `.ai/tasks/` for substantial multi-file work, reviews, or workflow changes.
- Use `.ai/task-packet-template.md` for new packets.
- Keep benchmark task definitions in `.ai/evals/tasks.yaml`.
- Record benchmark outcomes only after a real run in `.ai/evals/results.csv`; do not fabricate result rows.
