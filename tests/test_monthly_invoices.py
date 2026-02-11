import os
import sys
from pathlib import Path

import pytest

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


def test_month_window_invalid_month_raises():
    with pytest.raises(ValueError):
        monthly.month_window(2025, 13)


def test_normalize_providers_unknown_raises():
    with pytest.raises(ValueError):
        monthly.normalize_providers("gmail,unknown")


def test_merged_pythonpath_dedupes_and_prepends():
    extra = Path("/tmp/src")
    merged = monthly.merged_pythonpath(extra, f"{extra}{os.pathsep}/opt/other")
    assert merged.split(os.pathsep) == [str(extra), "/opt/other"]


def test_iter_invoice_pdfs_skips_special_dirs(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "keep.pdf").write_bytes(b"PDF")
    (root / "quarantine").mkdir()
    (root / "quarantine" / "skip.pdf").write_bytes(b"PDF")
    (root / "_tmp").mkdir()
    (root / "_tmp" / "skip.pdf").write_bytes(b"PDF")
    (root / "duplicates").mkdir()
    (root / "duplicates" / "skip.pdf").write_bytes(b"PDF")
    (root / "nested").mkdir()
    (root / "nested" / "also.pdf").write_bytes(b"PDF")
    found = {p.name for p in monthly.iter_invoice_pdfs(root)}
    assert found == {"keep.pdf", "also.pdf"}


def test_ensure_unique_adds_suffix(tmp_path):
    dest = tmp_path / "out"
    dest.mkdir()
    (dest / "file.pdf").write_bytes(b"PDF")
    unique = monthly.ensure_unique(dest, "file.pdf")
    assert unique.name == "file__2.pdf"


def test_preload_hashes_collects_existing(tmp_path):
    dest = tmp_path / "merged"
    dest.mkdir()
    a = dest / "a.pdf"
    b = dest / "b.pdf"
    a.write_bytes(b"A")
    b.write_bytes(b"B")
    hashes = monthly.preload_hashes(dest)
    assert len(hashes) == 2


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


def test_dedupe_provider_dir_text_fingerprint(monkeypatch, tmp_path):
    target = tmp_path / "gmail"
    target.mkdir()
    (target / "a.pdf").write_bytes(b"A")
    (target / "b.pdf").write_bytes(b"B")
    monkeypatch.setattr(monthly, "HAVE_PYMUPDF", True)

    def _fp(_path):
        return "same-fp"

    monkeypatch.setattr(monthly, "text_fingerprint", _fp)
    stats = monthly.dedupe_provider_dir(target)
    assert stats["kept"] == 1
    assert stats["moved"] == 1


def test_build_runs_requires_graph_client_id():
    with pytest.raises(SystemExit):
        monthly.build_runs(
            providers=["outlook"],
            python_bin="python",
            start_date="2025-01-01",
            end_date="2025-02-01",
            base_dir=Path("invoices"),
            month_label="01_2025",
            graph_client_id=None,
            gmail_extra_args="",
            graph_extra_args="",
        )


def test_build_runs_includes_extra_args(tmp_path):
    runs = monthly.build_runs(
        providers=["gmail"],
        python_bin="python",
        start_date="2025-01-01",
        end_date="2025-02-01",
        base_dir=tmp_path,
        month_label="01_2025",
        graph_client_id=None,
        gmail_extra_args="--verify --exclude-sent",
        graph_extra_args="",
    )
    assert runs[0].command[-2:] == ["--verify", "--exclude-sent"]


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


def test_run_all_sequential(monkeypatch):
    calls = []

    def _stub(run):
        calls.append(run.name)
        return monthly.ProviderResult(run.name, run.invoices_dir, run.command, 0)

    monkeypatch.setattr(monthly, "run_provider", _stub)
    runs = [
        monthly.ProviderRun("gmail", Path("a"), ["cmd"]),
        monthly.ProviderRun("outlook", Path("b"), ["cmd"]),
    ]
    results = monthly.run_all(runs, parallel=False)
    assert calls == ["gmail", "outlook"]
    assert all(r.returncode == 0 for r in results)


def test_write_summary_creates_manifest(tmp_path):
    dest = tmp_path / "merged"
    results = [monthly.ProviderResult("gmail", Path("g"), ["cmd"], 0)]
    monthly.write_summary(
        dest_dir=dest,
        start_date="2025-01-01",
        end_date="2025-02-01",
        label="01_2025",
        results=results,
        consolidation={"copied": 1},
        dedupe={"gmail": {"kept": 1}},
    )
    manifest = dest / "run_summary.json"
    assert manifest.exists()
