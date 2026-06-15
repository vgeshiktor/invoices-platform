# README Governance Discovery

Issue:
Execute the `readme-governance-discovery` benchmark task against the current repo state.

Desired outcome:
Contributors can find `AGENTS.md`, `PLANS.md`, and `.ai/README.md` directly from the root `README.md` without adding unsupported policy.

Explicit non-goals:
- Product behavior changes
- New governance files or process layers
- Changes outside discoverability wording in `README.md`

Relevant docs/files:
- `README.md`
- `AGENTS.md`
- `PLANS.md`
- `.ai/README.md`

Required validation:
- Confirm all linked governance paths exist.
- Confirm the README diff stays discoverability-only.
- Confirm no product code files changed for this milestone.

Known decisions:
- Existing local README governance-link changes are part of this milestone path.
- Reasoning level is `ai:light`.

Missing decisions:
None after inspecting the current repo files.

Reasoning level: `ai:light`

Maximum initial files: `6`
