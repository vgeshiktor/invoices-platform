import os
import sys
from argparse import Namespace
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


def test_fmt_duration():
    assert monthly.fmt_duration(0) == "00h:00m:00s"
    assert monthly.fmt_duration(65.2) == "00h:01m:05s"
    assert monthly.fmt_duration(3661) == "01h:01m:01s"


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
        stage_timings={"total_seconds": 1.0},
    )
    manifest = dest / "run_summary.json"
    assert manifest.exists()


def test_normalize_providers_empty_and_blank_entries():
    assert monthly.normalize_providers("") == ["gmail", "outlook"]
    assert monthly.normalize_providers(" , , ") == ["gmail", "outlook"]


def test_iter_invoice_pdfs_missing_root():
    missing = Path("/definitely/not/here")
    assert list(monthly.iter_invoice_pdfs(missing)) == []


def test_text_fingerprint_returns_none_without_pymupdf(monkeypatch, tmp_path):
    monkeypatch.setattr(monthly, "HAVE_PYMUPDF", False)
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"PDF")
    assert monthly.text_fingerprint(pdf) is None


def test_ensure_unique_increments_beyond_second(tmp_path):
    dest = tmp_path / "out"
    dest.mkdir()
    (dest / "file.pdf").write_bytes(b"1")
    (dest / "file__2.pdf").write_bytes(b"2")
    unique = monthly.ensure_unique(dest, "file.pdf")
    assert unique.name == "file__3.pdf"


def test_consolidate_pdfs_no_sources(tmp_path):
    stats = monthly.consolidate_pdfs(tmp_path / "dest", [])
    assert stats == {"copied": 0, "duplicates": 0, "sources": 0, "existing": 0}


def test_consolidate_pdfs_skips_missing_source(tmp_path):
    stats = monthly.consolidate_pdfs(tmp_path / "dest", [tmp_path / "missing"])
    assert stats["sources"] == 0
    assert stats["copied"] == 0


def test_consolidate_pdfs_hash_errors_are_skipped(monkeypatch, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    good = src / "good.pdf"
    bad = src / "bad.pdf"
    good.write_bytes(b"good")
    bad.write_bytes(b"bad")

    original_hash = monthly.hash_file

    def _hash(path):
        if path.name == "bad.pdf":
            raise RuntimeError("boom")
        return original_hash(path)

    monkeypatch.setattr(monthly, "hash_file", _hash)
    stats = monthly.consolidate_pdfs(tmp_path / "dest", [src])
    assert stats["copied"] == 1
    assert stats["duplicates"] == 0


def test_preload_hashes_skips_hash_errors(monkeypatch, tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    good = dest / "ok.pdf"
    bad = dest / "bad.pdf"
    good.write_bytes(b"ok")
    bad.write_bytes(b"bad")

    original_hash = monthly.hash_file

    def _hash(path):
        if path.name == "bad.pdf":
            raise OSError("broken")
        return original_hash(path)

    monkeypatch.setattr(monthly, "hash_file", _hash)
    hashes = monthly.preload_hashes(dest)
    assert len(hashes) == 1


def test_dedupe_provider_dir_missing_target(tmp_path):
    stats = monthly.dedupe_provider_dir(tmp_path / "missing")
    assert stats["scanned"] == 0
    assert stats["kept"] == 0


def test_dedupe_provider_dir_counts_hash_errors(monkeypatch, tmp_path):
    target = tmp_path / "provider"
    target.mkdir()
    (target / "a.pdf").write_bytes(b"A")

    def _hash(_path):
        raise RuntimeError("hash fail")

    monkeypatch.setattr(monthly, "hash_file", _hash)
    stats = monthly.dedupe_provider_dir(target)
    assert stats["errors"] == 1
    assert stats["scanned"] == 1


def test_dedupe_provider_dir_move_error_increments_errors(monkeypatch, tmp_path):
    target = tmp_path / "provider"
    target.mkdir()
    (target / "a.pdf").write_bytes(b"SAME")
    (target / "a__2.pdf").write_bytes(b"SAME")

    def _move(_src, _dest):
        raise OSError("cannot move")

    monkeypatch.setattr(monthly.shutil, "move", _move)
    stats = monthly.dedupe_provider_dir(target)
    assert stats["errors"] == 1
    assert stats["moved"] == 0


def test_build_runs_outlook_uses_graph_authority_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GRAPH_AUTHORITY", "common")
    runs = monthly.build_runs(
        providers=["outlook"],
        python_bin="python",
        start_date="2025-01-01",
        end_date="2025-02-01",
        base_dir=tmp_path,
        month_label="01_2025",
        graph_client_id="cid",
        gmail_extra_args="",
        graph_extra_args="--exclude-sent",
    )
    cmd = runs[0].command
    assert "--authority" in cmd
    assert cmd[cmd.index("--authority") + 1] == "common"
    assert cmd[-1] == "--exclude-sent"


def test_run_provider_calls_gmail_runner(monkeypatch, tmp_path):
    from invplatform.cli import gmail_invoice_finder as gmail_finder

    seen = {}

    def _run(argv):
        seen["argv"] = argv
        return 0

    monkeypatch.setattr(gmail_finder, "run", _run)
    run = monthly.ProviderRun(
        "gmail",
        tmp_path / "gmail",
        [
            "python",
            "-m",
            "invplatform.cli.gmail_invoice_finder",
            "--start-date",
            "2025-01-01",
        ],
    )
    result = monthly.run_provider(run)
    assert result.returncode == 0
    assert seen["argv"] == ["--start-date", "2025-01-01"]


def test_run_provider_handles_systemexit_and_exception(monkeypatch, tmp_path):
    from invplatform.cli import graph_invoice_finder as graph_finder

    monkeypatch.setattr(
        graph_finder, "run", lambda _argv: (_ for _ in ()).throw(SystemExit(7))
    )
    run = monthly.ProviderRun(
        "outlook",
        tmp_path / "outlook",
        ["python", "-m", "invplatform.cli.graph_invoice_finder"],
    )
    assert monthly.run_provider(run).returncode == 7

    monkeypatch.setattr(
        graph_finder, "run", lambda _argv: (_ for _ in ()).throw(RuntimeError("x"))
    )
    assert monthly.run_provider(run).returncode == 1


def test_run_provider_unknown_provider_raises(tmp_path):
    run = monthly.ProviderRun("unknown", tmp_path / "x", ["cmd"])
    with pytest.raises(ValueError):
        monthly.run_provider(run)


def test_run_all_empty_returns_empty():
    assert monthly.run_all([], parallel=True) == []


def test_parse_args_reads_env_defaults(monkeypatch):
    monkeypatch.setenv("MONTHLY_GMAIL_ARGS", "--verify")
    monkeypatch.setenv("MONTHLY_GRAPH_ARGS", "--exclude-sent")
    monkeypatch.setenv("GRAPH_CLIENT_ID", "client-from-env")
    monkeypatch.setattr(
        sys,
        "argv",
        ["monthly_invoices", "--providers", "gmail", "--base-dir", "/tmp/out"],
    )
    args = monthly.parse_args()
    assert args.gmail_extra_args == "--verify"
    assert args.graph_extra_args == "--exclude-sent"
    assert args.graph_client_id == "client-from-env"


def test_main_no_runs_exits_early(monkeypatch, capsys):
    monkeypatch.setattr(
        monthly,
        "parse_args",
        lambda: Namespace(
            year=2025,
            month=1,
            base_dir="invoices",
            providers="gmail",
            python_bin="python",
            graph_client_id=None,
            gmail_extra_args="",
            graph_extra_args="",
            sequential=False,
        ),
    )
    monkeypatch.setattr(monthly, "build_runs", lambda **_kwargs: [])
    monthly.main()
    assert "nothing to do" in capsys.readouterr().out.lower()


def test_main_happy_path_and_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(
        monthly,
        "parse_args",
        lambda: Namespace(
            year=2025,
            month=1,
            base_dir=str(tmp_path),
            providers="gmail,outlook",
            python_bin="python",
            graph_client_id="cid",
            gmail_extra_args="",
            graph_extra_args="",
            sequential=True,
        ),
    )

    runs = [
        monthly.ProviderRun("gmail", tmp_path / "gmail", ["cmd"]),
        monthly.ProviderRun("outlook", tmp_path / "outlook", ["cmd"]),
    ]
    monkeypatch.setattr(monthly, "build_runs", lambda **_kwargs: runs)
    monkeypatch.setattr(
        monthly, "month_window", lambda _y, _m: ("2025-01-01", "2025-02-01", "01_2025")
    )
    monkeypatch.setattr(monthly, "normalize_providers", lambda _p: ["gmail", "outlook"])

    success_results = [
        monthly.ProviderResult("gmail", tmp_path / "gmail", ["cmd"], 0, 0.1),
        monthly.ProviderResult("outlook", tmp_path / "outlook", ["cmd"], 0, 0.1),
    ]
    calls = {"dedupe": [], "summary": 0}
    monkeypatch.setattr(monthly, "run_all", lambda _runs, parallel: success_results)
    monkeypatch.setattr(
        monthly,
        "dedupe_provider_dir",
        lambda path: calls["dedupe"].append(path) or {"kept": 1, "moved": 0},
    )
    monkeypatch.setattr(
        monthly,
        "consolidate_pdfs",
        lambda _dest, _sources: {
            "copied": 1,
            "duplicates": 0,
            "sources": 2,
            "existing": 0,
        },
    )
    monkeypatch.setattr(
        monthly,
        "write_summary",
        lambda *_args, **_kwargs: calls.__setitem__("summary", calls["summary"] + 1),
    )
    monthly.main()
    assert len(calls["dedupe"]) == 2
    assert calls["summary"] == 1

    failed_results = [
        monthly.ProviderResult("gmail", tmp_path / "gmail", ["cmd"], 1, 0.1),
    ]
    monkeypatch.setattr(monthly, "run_all", lambda _runs, parallel: failed_results)
    with pytest.raises(SystemExit):
        monthly.main()
