from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
AGENTS_GUIDE = ROOT / "AGENTS.md"
AI_README = ROOT / ".ai" / "README.md"
TASK_PACKET_TEMPLATE = ROOT / ".ai" / "task-packet-template.md"
EVAL_TASKS = ROOT / ".ai" / "evals" / "tasks.yaml"
DAY2_INTEROP_TASK_PACKET = (
    ROOT / ".ai" / "tasks" / "2026-06-21-day2-interoperability-governance.md"
)
DAY3_SKILL_GOVERNANCE_TASK_PACKET = (
    ROOT / ".ai" / "tasks" / "2026-06-25-day3-skill-governance.md"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_makefile_defines_verify_target_with_required_checks():
    makefile = _read(MAKEFILE)

    phony_lines = [line for line in makefile.splitlines() if line.startswith(".PHONY:")]
    assert any(" verify" in f" {line} " for line in phony_lines)
    assert "\nverify:" in makefile
    assert "$(MAKE) verify-python" in makefile
    assert "$(MAKE) verify-go" in makefile
    assert "$(MAKE) verify-module-tidiness" in makefile
    assert "$(MAKE) verify-artifact-schemas" in makefile
    assert "$(MAKE) verify-generated-artifact-secrets" in makefile
    assert "git status --porcelain=v1 --untracked-files=all" in makefile
    assert "ruff check apps/workers-py" in makefile
    assert "ruff format --check apps/workers-py" in makefile
    assert "pytest -q tests" in makefile
    assert "gofmt -l" in makefile
    assert "go vet ./..." in makefile
    assert "go test ./..." in makefile
    assert "mktemp -d" in makefile
    assert "cp -R apps/api-go/." in makefile
    assert 'cd "$$tmp_dir" && go mod tidy' in makefile
    assert 'diff -u apps/api-go/go.mod "$$tmp_dir/go.mod"' in makefile
    assert "go mod tidy -diff" not in makefile
    assert "scripts/validate_artifact_schemas.py" in makefile
    assert "scripts/check_generated_artifact_secrets.py" in makefile


def test_ci_workflow_uses_make_verify():
    workflow = _read(CI_WORKFLOW)

    assert "make verify" in workflow
    assert "ruff check --fix apps/workers-py" not in workflow
    assert "pytest tests/test_invoice_finders.py" not in workflow


def test_repo_governance_docs_define_lean_ctx_workflow_contract():
    agents_guide = _read(AGENTS_GUIDE)
    ai_readme = _read(AI_README)
    task_packet_template = _read(TASK_PACKET_TEMPLATE)
    eval_tasks = _read(EVAL_TASKS)
    day2_task_packet = _read(DAY2_INTEROP_TASK_PACKET)
    day3_task_packet = _read(DAY3_SKILL_GOVERNANCE_TASK_PACKET)

    assert "## Agentic Engineering Defaults" in agents_guide
    assert "working mode: `prototype` for exploration or `production`" in agents_guide
    assert "shipping changes must define the required tests" in agents_guide
    assert "Review AI-generated code with equal or higher scrutiny" in agents_guide
    assert (
        "convert the lesson into a repo rule, template field, example, or test"
        in agents_guide
    )
    assert "## Interoperability Defaults" in agents_guide
    assert "bounded, schema-driven, fire-and-forget operations" in agents_guide
    assert "unbounded, ambiguous, multi-turn work" in agents_guide
    assert "search for an existing vetted tool, server, or skill first" in agents_guide
    assert "official, internal, or otherwise vetted registries" in agents_guide
    assert (
        "public or unverified tool servers as production dependencies" in agents_guide
    )
    assert (
        "require explicit human approval before side-effectful or sensitive external tool calls"
        in agents_guide
    )
    assert "declarative or trusted-catalog UI contracts" in agents_guide
    assert "Defer AP2/UCP-style payment or procurement flows" in agents_guide
    assert "## Skill Governance Defaults" in agents_guide
    assert "Skills are for narrow, repeatable workflows" in agents_guide
    assert "Always-on project conventions belong in `AGENTS.md`" in agents_guide
    assert "first-party, internal, or otherwise vetted skills first" in agents_guide
    assert "Pin adopted skills to a reviewed version or commit" in agents_guide
    assert "one skill, one job" in agents_guide
    assert "what it does, when to use it, and when not to use it" in agents_guide
    assert "progressive disclosure" in agents_guide
    assert "deterministic helper logic in `scripts/`" in agents_guide
    assert (
        "Do not hard-code secrets, credentials, or machine-specific paths"
        in agents_guide
    )
    assert "portable across compliant runtimes" in agents_guide
    assert "read-only" in agents_guide
    assert "sanitized" in agents_guide

    assert "## Lean-ctx Workflow" in agents_guide
    assert "start with `ctx_overview`" in agents_guide
    assert "Use `ctx_tree`" in agents_guide
    assert "Use `ctx_search` before broad reads" in agents_guide
    assert "`ctx_read` or `ctx_multi_read`" in agents_guide
    assert '`ctx_shell` or `lean-ctx -c "<command>"`' in agents_guide
    assert (
        "exact uncompressed output is required or lean-ctx is unavailable"
        in agents_guide
    )
    assert "upstream tooling issue rather than a repo-policy exception" in agents_guide
    assert "use `lean-ctx-off`" in agents_guide

    assert "## Harness Map" in ai_readme
    assert "Instructions and guardrails: `AGENTS.md`" in ai_readme
    assert "Current-state memory: `PLANS.md`" in ai_readme
    assert "Task memory and spec: `.ai/tasks/`" in ai_readme
    assert "Eval contracts: `.ai/evals/tasks.yaml`" in ai_readme
    assert "Validation tools and contract checks: `Makefile` and `tests/`" in ai_readme

    assert "## Lean-ctx-First Workflow" in ai_readme
    assert "Follow `AGENTS.md` as the canonical lean-ctx policy" in ai_readme
    assert "Start with `ctx_overview`" in ai_readme
    assert '`ctx_shell` or `lean-ctx -c "<command>"`' in ai_readme
    assert "record the reason in the task packet" in ai_readme
    assert "`lean-ctx gain --deep`" in ai_readme
    assert "## Interoperability Review Gate" in ai_readme
    assert (
        "integration mode: `tool | collaborator-agent | ui-contract | commerce-deferred`"
        in ai_readme
    )
    assert (
        "trust level: `official | internal | third-party-vetted | public-prototype-only`"
        in ai_readme
    )
    assert (
        "data scope: `synthetic | sanitized | real-nonprod | real-prod-readonly`"
        in ai_readme
    )
    assert "read-only scope when possible" in ai_readme
    assert "HITL approval point" in ai_readme
    assert "## Skill Governance Review Gate" in ai_readme
    assert (
        "use the existing task-packet fields rather than adding a skill-specific template"
        in ai_readme
    )
    assert "external-skill adoption work" in ai_readme
    assert "future repo-local skill authoring work" in ai_readme
    assert "`trigger`, `execution`, `regression`, and `token budget`" in ai_readme

    assert "Working mode: `prototype | production`" in task_packet_template
    assert "Success criteria / eval rubric:" in task_packet_template
    assert "AI-specific review focus:" in task_packet_template
    assert "Harness components touched:" in task_packet_template
    assert (
        "Integration mode: `tool | collaborator-agent | ui-contract | commerce-deferred`"
        in task_packet_template
    )
    assert "External dependency or registry:" in task_packet_template
    assert (
        "Trust level: `official | internal | third-party-vetted | public-prototype-only`"
        in task_packet_template
    )
    assert (
        "Data scope: `synthetic | sanitized | real-nonprod | real-prod-readonly`"
        in task_packet_template
    )
    assert "HITL approval point:" in task_packet_template
    assert "Write permission / read-only expectation:" in task_packet_template
    assert "Transport/schema debugging plan:" in task_packet_template

    assert "Overview/search plan:" in task_packet_template
    assert "Lean-ctx structure check (`ctx_tree`) scope:" in task_packet_template
    assert "Lean-ctx search plan (`ctx_search`):" in task_packet_template
    assert (
        "Intended file reads (`ctx_read` / `ctx_multi_read`):" in task_packet_template
    )
    assert (
        "Intended compressed shell commands (`ctx_shell` / `lean-ctx -c`):"
        in task_packet_template
    )
    assert "Raw/native fallback justification:" in task_packet_template

    assert "mode: production" in eval_tasks
    assert "rubric:" in eval_tasks
    assert "ship_gate:" in eval_tasks
    assert "- id: lean-ctx-governance-review" in eval_tasks
    assert "Review lean-ctx routing guidance and fallback rules" in eval_tasks
    assert "Contract coverage protects the policy" in eval_tasks
    assert "- id: agentic-alignment-governance-review" in eval_tasks
    assert "- id: day2-interoperability-governance-review" in eval_tasks
    assert "- id: day3-skill-governance-review" in eval_tasks
    assert (
        "Review Day 3 skill governance defaults and skill-library guardrails"
        in eval_tasks
    )
    assert (
        "Review Day 2 interoperability governance defaults and guardrails" in eval_tasks
    )
    assert (
        "tool vs collaborator-agent vs ui-contract classification stays explicit"
        in eval_tasks
    )
    assert "HITL, trust level, and real-data scope rules remain aligned" in eval_tasks
    assert "AGENTS.md vs Skills vs MCP/tool boundaries stay explicit" in eval_tasks
    assert "source selection and pinning rules stay reviewable" in eval_tasks
    assert (
        "progressive disclosure and portability rules remain discoverable" in eval_tasks
    )
    assert (
        "trigger, execution, regression, and token-budget expectations stay explicit"
        in eval_tasks
    )
    assert (
        "unsupported policy claims, missing review gates, or doc/test drift"
        in eval_tasks
    )

    assert "Working mode: `production`" in day2_task_packet
    assert "Integration mode: `commerce-deferred`" in day2_task_packet
    assert "Trust level: `official`" in day2_task_packet
    assert "Data scope: `sanitized`" in day2_task_packet
    assert "HITL approval point:" in day2_task_packet
    assert "Write permission / read-only expectation:" in day2_task_packet
    assert "Transport/schema debugging plan:" in day2_task_packet

    assert "Desired outcome:" in day3_task_packet
    assert "governance-only" in day3_task_packet
    assert "Working mode: `production`" in day3_task_packet
    assert "External dependency or registry:" in day3_task_packet
    assert "official guidance source" in day3_task_packet
    assert "docs/contract-test enforcement only" in day3_task_packet
    assert "Trust level: `official`" in day3_task_packet
    assert "Data scope: `sanitized`" in day3_task_packet
