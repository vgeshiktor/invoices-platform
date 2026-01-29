import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "apps" / "workers-py" / "src"
sys.path.insert(0, str(SRC_DIR))

from invplatform.cli import monthly_invoices as monthly  # noqa: E402


def test_month_window_handles_december():
    start, end, label = monthly.month_window(2025, 12)
    assert start == "2025-12-01"
    assert end == "2026-01-01"
    assert label == "12_2025"


def test_normalize_providers_aliases_and_order():
    providers = monthly.normalize_providers("gmail,graph,outlook")
    assert providers == ["gmail", "outlook"]
    providers = monthly.normalize_providers("outlook,gmail,outlook")
    assert providers == ["outlook", "gmail"]


def test_consolidate_skips_quarantine_and_dedup(tmp_path):
    src1 = tmp_path / "gmail"
    src2 = tmp_path / "outlook"
    dest = tmp_path / "merged"

    src1.mkdir()
    src2.mkdir()
    (src1 / "inv1.pdf").write_bytes(b"PDF-A")
    (src1 / "quarantine").mkdir()
    (src1 / "quarantine" / "skip.pdf").write_bytes(b"PDF-SKIP")

    src2.mkdir(exist_ok=True)
    (src2 / "inv2.pdf").write_bytes(b"PDF-B")
    (src2 / "_tmp").mkdir()
    (src2 / "_tmp" / "skip.pdf").write_bytes(b"PDF-SKIP2")
    # Duplicate content should be detected.
    (src2 / "dup.pdf").write_bytes(b"PDF-A")

    stats = monthly.consolidate_pdfs(dest, [src1, src2])
    assert stats["sources"] == 2
    assert stats["copied"] == 2  # inv1 + inv2
    assert stats["duplicates"] == 1
    saved = list(dest.glob("*.pdf"))
    assert len(saved) == 2


def test_dedupe_provider_dir_moves_duplicates(tmp_path):
    target = tmp_path / "gmail"
    target.mkdir()
    (target / "a.pdf").write_bytes(b"PDF-A")
    (target / "a__2.pdf").write_bytes(b"PDF-A")  # duplicate content
    (target / "b.pdf").write_bytes(b"PDF-B")
    stats = monthly.dedupe_provider_dir(target)
    assert stats["kept"] == 2
    assert stats["moved"] == 1
    dup_dir = target / "duplicates"
    assert dup_dir.exists()
    moved = list(dup_dir.glob("*.pdf"))
    assert len(moved) == 1


def test_run_all_uses_parallel_flag(monkeypatch):
    calls = []

    def _stub(run):
        calls.append(run.name)
        return monthly.ProviderResult(run.name, run.invoices_dir, run.command, 0)

    monkeypatch.setattr(monthly, "run_provider", _stub)
    runs = [
        monthly.ProviderRun("gmail", Path("a"), ["cmd"]),
        monthly.ProviderRun("outlook", Path("b"), ["cmd"]),
    ]
    results = monthly.run_all(runs, parallel=True)
    assert sorted(calls) == ["gmail", "outlook"]
    assert all(r.returncode == 0 for r in results)
