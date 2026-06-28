# Task Packet
Desired outcome:
Align repo governance artifacts with Day 4 agent security and evaluation guidance without adding runtime observability, new scanners, or product-surface changes.
Explicit non-goals:
- no runtime observability, sandboxing infrastructure, SAST/SCA setup, or online-eval rollout in this pass
- No OpenTelemetry traces, AgBOMs, circuit breakers, or checkpoint infrastructure.
- No benchmark result rows in `.ai/evals/results.csv`.
Relevant docs/files:
- `AGENTS.md`
- `PLANS.md`
- `.ai/README.md`
- `.ai/evals/tasks.yaml`
- `docs/SECURITY-AND-DATA-HANDLING.md`
- `tests/test_repo_verify_contract.py`
- `tests/test_eval_catalog_contract.py`
Required validation:
- `pytest -q tests/test_repo_verify_contract.py tests/test_eval_catalog_contract.py`
Known decisions:
- Scope is governance-only.
- This pass covers both agent security and evaluation guidance.
- Enforcement stays at the docs/contract-test enforcement only layer.
- Existing `.ai` fields remain sufficient; no template expansion in this pass.
Missing decisions:
- None for this pass.
Working mode: `production`
Success criteria / eval rubric:
- Repo guidance documents a security posture for untrusted generated code, governed egress, narrow permissions, and high-risk approvals.
- Repo guidance documents evaluation expectations for intent, correctness, convention matching, trajectory quality, and self-repair without inventing runtime telemetry.
- Day-4 language stays repo-backed and clearly distinguishes current governance rules from deferred future infrastructure.
AI-specific review focus:
- Unsupported security or observability claims
- Missing separation between boundary safety and shipping quality
- Drift between docs, task packet, eval catalog, security guidance, and contract tests
Harness components touched:
- instructions/guardrails
- task memory/spec
- eval contracts
- security guidance
- validation/tools
Integration mode: `tool`
External dependency or registry:
- official guidance source: `Vibe Coding Agent Security and Evaluation_Day_4.pdf` plus existing repo governance files
Trust level: `official`
Data scope: `sanitized`
HITL approval point:
- Before any high-risk or irreversible action, especially when generated code or new dependencies would touch sensitive systems or non-read-only data
Write permission / read-only expectation:
- Governance docs are writable; autonomous or AI-assisted sensitive work should default to bounded read-only or non-production scopes when possible
Transport/schema debugging plan:
- Keep this pass at the governance layer; do not introduce runtime tracing or scanner infrastructure in this change
Reasoning level: `ai:review`
max initial files: `6`
Overview/search plan:
- Review existing day 1-3 governance assets first, then add only the day-4 security and evaluation deltas that fit current repo maturity
Lean-ctx structure check (`ctx_tree`) scope:
- repo root, `.ai/`, `docs/`, and `tests/`
Lean-ctx search plan (`ctx_search`):
- security, evaluation, observability, scanner, egress, trust, and trajectory terms
Intended file reads (`ctx_read` / `ctx_multi_read`):
- repo governance docs, eval catalog, security guidance, and repo contract tests
Intended compressed shell commands (`ctx_shell` / `lean-ctx -c`):
- `lean-ctx -c "pytest -q tests/test_repo_verify_contract.py tests/test_eval_catalog_contract.py"`
Raw/native fallback justification:
- Use raw/native access only if exact uncompressed output is needed to debug a lean-ctx or PDF-inspection limitation

---
