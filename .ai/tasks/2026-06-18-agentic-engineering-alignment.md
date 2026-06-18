# Task Packet

Issue:
Align repo governance artifacts with the Day 1 agentic-engineering recommendations without adding runtime infrastructure.

Desired outcome:
- Governance docs define prototype vs production expectations for substantial AI-assisted work.
- `.ai/` assets map the repo harness to concrete files and structured review/eval expectations.
- Repo contract tests protect the new governance fields and review template structure.

Explicit non-goals:
- Add repo-local skills, telemetry, traces, or model-routing infrastructure.
- Change `README.md`, `docs/USAGE.md`, product code, or runtime behavior.
- Add benchmark result rows without a real eval run.

Relevant docs/files:
- `AGENTS.md`
- `PLANS.md`
- `.ai/README.md`
- `.ai/task-packet-template.md`
- `.ai/evals/tasks.yaml`
- `tests/test_repo_verify_contract.py`

Required validation:
- `pytest -q tests/test_repo_verify_contract.py`
- `make verify` if governance contract changes extend beyond the targeted repo-contract test

Known decisions:
- Treat the existing lean-ctx governance edits as the baseline to extend.
- Keep this pass at the governance/workflow layer only.
- Use repo docs, templates, and contract tests rather than telemetry for enforcement.

Missing decisions:
- None.

Working mode: `production`
Success criteria / eval rubric:
- Repo guidance clearly distinguishes `prototype` and `production` work.
- Harness/file mapping is discoverable from `.ai/README.md`.
- Review templates expose `mode`, `rubric`, and `ship_gate`.
- Repo contract tests fail if these governance requirements drift.
AI-specific review focus:
- Unsupported governance claims
- Missing review gates or test/eval expectations
- Drift between docs, templates, and repo contract tests
Harness components touched:
- instructions/guardrails
- task memory/spec
- eval contracts
- validation/tools
Reasoning level: `ai:standard`
max initial files: `6`
Overview/search plan:
- Start with `ctx_overview`, then confirm current governance surfaces and in-flight edits before patching.
Lean-ctx structure check (`ctx_tree`) scope:
- Repo root, `.ai/`, and `tests/`.
Lean-ctx search plan (`ctx_search`):
- Search for existing governance, eval, and lean-ctx contract language before editing.
Intended file reads (`ctx_read` / `ctx_multi_read`):
- Governance docs, task template, eval catalog, and repo contract tests.
Intended compressed shell commands (`ctx_shell` / `lean-ctx -c`):
- `lean-ctx -c "git status --short"`
- `lean-ctx -c "pytest -q tests/test_repo_verify_contract.py"`
Raw/native fallback justification:
- Use raw/native access only if exact uncompressed output is needed to debug a lean-ctx/tooling failure.

---
