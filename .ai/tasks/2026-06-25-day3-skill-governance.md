# Task Packet
Desired outcome:
Align repo governance artifacts with Day 3 skill-governance guidance without adding a repo-local skill library, runtime enforcement, or product-surface changes.
Explicit non-goals:
- No repo-local `SKILL.md` creation.
- No runtime routing, skill linting, telemetry, or CI execution changes.
- No benchmark result rows in `.ai/evals/results.csv`.
Relevant docs/files:
- `AGENTS.md`
- `PLANS.md`
- `.ai/README.md`
- `.ai/evals/tasks.yaml`
- `docs/SECURITY-AND-DATA-HANDLING.md`
- `tests/test_repo_verify_contract.py`
Required validation:
- `pytest -q tests/test_repo_verify_contract.py`
Known decisions:
- Scope is governance-only.
- This pass covers both external-skill adoption and future repo-local skill authoring standards.
- Enforcement stays at the docs/contract-test enforcement only layer.
Missing decisions:
- None for this pass.
Working mode: `production`
Success criteria / eval rubric:
- Repo rules clearly distinguish `AGENTS.md`, Skills, and tools/MCP surfaces.
- Source selection, pinning, progressive disclosure, and portability rules remain repo-backed and reviewable.
- Skill-governance expectations define `trigger`, `execution`, `regression`, and `token budget` coverage without inventing runtime enforcement.
AI-specific review focus:
- Unsupported governance claims
- Missing review gates or pinned-dependency expectations
- Drift between docs, task packet, eval catalog, security guidance, and contract tests
Harness components touched:
- instructions/guardrails
- task memory/spec
- eval contracts
- security guidance
- validation/tools
Integration mode: `tool`
External dependency or registry:
- official guidance source: `Agent Skills_Day_3.pdf` recommendations plus existing repo governance files
Trust level: `official`
Data scope: `sanitized`
HITL approval point:
- Before any future action-allowed or sensitive skill is adopted for shared workflows
Write permission / read-only expectation:
- Governance docs are writable; external or real-data skill usage should default to read-only when unavoidable
Transport/schema debugging plan:
- Keep this pass at the governance layer; use repo docs and contract tests rather than runtime instrumentation
Reasoning level: `ai:review`
max initial files: `6`
Overview/search plan:
- Review the existing Day 1 and Day 2 governance assets first, then add only the Day 3 skill-governance deltas that fit the current repo maturity
Lean-ctx structure check (`ctx_tree`) scope:
- repo root, `.ai/`, and `docs/`
Lean-ctx search plan (`ctx_search`):
- skill, governance, eval, progressive disclosure, and security-handling terms
Intended file reads (`ctx_read` / `ctx_multi_read`):
- repo governance docs, eval catalog, security guidance, and repo contract tests
Intended compressed shell commands (`ctx_shell` / `lean-ctx -c`):
- `lean-ctx -c "pytest -q tests/test_repo_verify_contract.py"`
Raw/native fallback justification:
- Use raw/native access only if exact uncompressed output is needed to debug a lean-ctx or PDF-inspection limitation

---
