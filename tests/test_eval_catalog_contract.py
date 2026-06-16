import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASKS_YAML = ROOT / ".ai" / "evals" / "tasks.yaml"
MAKEFILE = ROOT / "Makefile"
FIXTURE_DIR = ROOT / ".ai" / "evals" / "fixtures" / "cross-provider-dedup"
SCRIPT = ROOT / "scripts" / "eval_cross_provider_dedup.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_eval_catalog_defines_cross_provider_dedup_scenario():
    tasks_yaml = _read(TASKS_YAML)

    assert "- id: cross-provider-dedup" in tasks_yaml
    assert "fixture: .ai/evals/fixtures/cross-provider-dedup/" in tasks_yaml
    assert "command: make eval-cross-provider-dedup" in tasks_yaml
    assert "invoice_count: 1" in tasks_yaml
    assert "duplicate_count: 1" in tasks_yaml
    assert "threshold: pass" in tasks_yaml
    assert "credential_content_in_logs" in tasks_yaml
    assert "modification_outside_temp_dir" in tasks_yaml


def test_makefile_defines_eval_cross_provider_dedup_target():
    makefile = _read(MAKEFILE)

    assert "eval-cross-provider-dedup" in makefile
    assert "scripts/eval_cross_provider_dedup.py" in makefile


def test_cross_provider_dedup_eval_runner_is_runnable_and_non_destructive(tmp_path):
    before = {
        path.relative_to(FIXTURE_DIR): path.read_bytes()
        for path in sorted(FIXTURE_DIR.rglob("*"))
        if path.is_file()
    }

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--fixture",
            str(FIXTURE_DIR),
            "--work-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["invoice_count"] == 1
    assert payload["duplicate_count"] == 1
    assert payload["forbidden_violations"] == []
    assert "credential" not in result.stdout.lower()
    assert "authorization" not in result.stdout.lower()

    after = {
        path.relative_to(FIXTURE_DIR): path.read_bytes()
        for path in sorted(FIXTURE_DIR.rglob("*"))
        if path.is_file()
    }
    assert after == before
