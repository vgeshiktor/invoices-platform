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
