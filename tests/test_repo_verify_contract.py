from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_makefile_defines_verify_target_with_required_checks():
    makefile = _read(MAKEFILE)

    phony_lines = [line for line in makefile.splitlines() if line.startswith(".PHONY:")]
    assert any(" verify" in f" {line} " for line in phony_lines)
    assert "\nverify:" in makefile
    assert "ruff check apps/workers-py" in makefile
    assert "ruff format --check apps/workers-py" in makefile
    assert "pytest -q tests" in makefile
    assert "gofmt -l" in makefile
    assert "go vet ./..." in makefile
    assert "go test ./..." in makefile
    assert "go mod tidy" in makefile
    assert "git diff --exit-code -- apps/api-go/go.mod apps/api-go/go.sum" in makefile
    assert "scripts/validate_artifact_schemas.py" in makefile
    assert "scripts/check_generated_artifact_secrets.py" in makefile


def test_ci_workflow_uses_make_verify():
    workflow = _read(CI_WORKFLOW)

    assert "make verify" in workflow
    assert "ruff check --fix apps/workers-py" not in workflow
    assert "pytest tests/test_invoice_finders.py" not in workflow
