# Task Packet
Desired outcome:
Align repo governance artifacts with Day 2 interoperability guidance without changing runtime product surfaces.
Explicit non-goals:
- No runtime A2A, A2UI, AP2, or UCP implementation.
- No OpenAPI or product-doc behavior changes.
Relevant docs/files:
- AGENTS.md
- PLANS.md
- .ai/README.md
- .ai/task-packet-template.md
- .ai/evals/tasks.yaml
- tests/test_repo_verify_contract.py
- docs/SECURITY-AND-DATA-HANDLING.md
Required validation:
- `pytest -q tests/test_repo_verify_contract.py`
Known decisions:
- Working mode is production because this updates shared repo governance.
- Scope is governance-only; protocol runtime work stays deferred.
- Existing dirty changes outside governance files must be preserved.
Missing decisions:
- None for this pass.
Working mode: `production`
Success criteria / eval rubric:
- Repo rules distinguish tool, collaborator-agent, ui-contract, and commerce-deferred work.
- Task packet and eval contracts capture trust, data-scope, HITL, and read-only expectations.
- Contract coverage protects the new guidance without inventing runtime enforcement.
AI-specific review focus:
- Unsupported policy claims
- Security drift against existing data-handling guidance
- Overreach beyond current repo maturity
Harness components touched:
- repo rules
- task-packet contract
- eval task catalog
- repo contract tests
Integration mode: `commerce-deferred`
External dependency or registry:
- Day 2 PDF recommendations only; no new runtime dependency introduced
Trust level: `official`
Data scope: `sanitized`
HITL approval point:
- Before any future side-effectful or sensitive external integration is added to the repo
Write permission / read-only expectation:
- Governance files are writable; external real-data integrations should default to read-only when unavoidable
Transport/schema debugging plan:
- Keep debugging guidance at the policy level; use existing lean-ctx workflow and documented contract tests for this pass
Reasoning level: `ai:review`
max initial files: `6`
Overview/search plan:
- Review existing governance assets first, then add Day 2 deltas only where the repo already has stable governance hooks
Lean-ctx structure check (`ctx_tree`) scope:
- repo root and `.ai/`
Lean-ctx search plan (`ctx_search`):
- interoperability, agentic, lean-ctx, security, review-gate terms
Intended file reads (`ctx_read` / `ctx_multi_read`):
- governance docs, task-packet template, eval tasks, contract tests
Intended compressed shell commands (`ctx_shell` / `lean-ctx -c`):
- targeted pytest for repo contract verification
Raw/native fallback justification:
- None expected
