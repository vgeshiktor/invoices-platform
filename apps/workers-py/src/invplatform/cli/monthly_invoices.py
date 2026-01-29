#!/usr/bin/env python3
"""
monthly_invoices.py
-------------------

Convenience wrapper that runs the Gmail and Outlook invoice fetchers for a
single target month (default: the current month), drops results into
provider-specific folders under a common invoices/ root, and consolidates all
PDFs into a merged monthly folder.

Key behaviors:
- Computes [start_date, end_date) for the month and builds folder labels
  like invoices_gmail_11_2025 and invoices_outlook_11_2025.
- Launches the existing CLI scripts (gmail_invoice_finder, graph_invoice_finder)
  in parallel by default, with PYTHONPATH preconfigured.
- Consolidates PDFs into invoices_11_2025 while deduplicating by SHA-256 and
  skipping quarantine/_tmp content.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from invplatform.domain import pdf as domain_pdf


PROJECT_SRC = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_SRC.parents[2]
DEFAULT_PYTHON = os.environ.get("PYTHON") or sys.executable
SKIP_DIRS = {"_tmp", "quarantine", "duplicates"}
HAVE_PYMUPDF = getattr(domain_pdf, "HAVE_PYMUPDF", False)

# Ensure direct execution works without exporting PYTHONPATH first.
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))


@dataclass
class ProviderRun:
    name: str
    invoices_dir: Path
    command: List[str]


@dataclass
class ProviderResult:
    name: str
    invoices_dir: Path
    command: List[str]
    returncode: int


def month_window(year: int | None, month: int | None) -> Tuple[str, str, str]:
    """Return (start_date, end_date, label) for the requested month."""
    today = dt.date.today()
    target_year = year or today.year
    target_month = month or today.month
    if target_month < 1 or target_month > 12:
        raise ValueError("month must be between 1 and 12")
    first = dt.date(target_year, target_month, 1)
    # Advance safely to the first of next month.
    next_month = (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    start_date = first.strftime("%Y-%m-%d")
    end_date = next_month.strftime("%Y-%m-%d")
    label = first.strftime("%m_%Y")
    return start_date, end_date, label


def normalize_providers(raw: str) -> List[str]:
    """Parse comma-separated provider list and normalize aliases."""
    if not raw:
        return ["gmail", "outlook"]
    providers = []
    for entry in raw.split(","):
        p = entry.strip().lower()
        if not p:
            continue
        if p in {"graph", "msgraph", "outlook", "microsoft"}:
            providers.append("outlook")
        elif p == "gmail":
            providers.append("gmail")
        else:
            raise ValueError(f"Unknown provider: {entry}")
    # Preserve order but drop duplicates.
    seen = set()
    deduped = []
    for p in providers:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped or ["gmail", "outlook"]


def merged_pythonpath(extra: Path, current: str | None) -> str:
    """Prepend project src to PYTHONPATH without duplicating entries."""
    parts = [str(extra)]
    if current:
        for chunk in current.split(os.pathsep):
            if chunk and chunk not in parts:
                parts.append(chunk)
    return os.pathsep.join(parts)


def hash_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def iter_invoice_pdfs(root: Path) -> Iterable[Path]:
    """Yield invoice PDFs under root, skipping quarantine/_tmp folders."""
    if not root.exists():
        return
    for path in root.rglob("*.pdf"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def stem_key(path: Path) -> str:
    stem = path.stem
    m = re.match(r"^(.*)__\d+$", stem)
    return m.group(1) if m else stem


def text_fingerprint(path: Path) -> str | None:
    if not HAVE_PYMUPDF:
        return None
    return domain_pdf.text_fingerprint(str(path))


def preload_hashes(dest_dir: Path) -> Dict[str, Path]:
    """Build digest index for existing PDFs in the consolidated folder."""
    hashes: Dict[str, Path] = {}
    for pdf in iter_invoice_pdfs(dest_dir):
        try:
            digest = hash_file(pdf)
            hashes[digest] = pdf
        except Exception:
            continue
    return hashes


def ensure_unique(dest_dir: Path, name: str) -> Path:
    """Return a non-clashing destination path under dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    candidate = dest_dir / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        candidate = dest_dir / f"{stem}__{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def consolidate_pdfs(dest_dir: Path, sources: Sequence[Path]) -> Dict[str, int]:
    """Copy PDFs from sources into dest_dir while deduplicating."""
    stats = {"copied": 0, "duplicates": 0, "sources": 0, "existing": 0}
    if not sources:
        return stats
    dest_dir.mkdir(parents=True, exist_ok=True)
    seen_hashes = preload_hashes(dest_dir)
    stats["existing"] = len(seen_hashes)
    seen = dict(seen_hashes)
    for src in sources:
        if not src.exists():
            continue
        stats["sources"] += 1
        for pdf in iter_invoice_pdfs(src):
            try:
                digest = hash_file(pdf)
            except Exception:
                continue
            if digest in seen:
                stats["duplicates"] += 1
                continue
            dest_path = ensure_unique(dest_dir, pdf.name)
            shutil.copy2(pdf, dest_path)
            seen[digest] = dest_path
            stats["copied"] += 1
    return stats


def dedupe_provider_dir(target_dir: Path) -> Dict[str, int]:
    """Remove/move duplicate PDFs inside a provider folder based on hash."""
    stats = {
        "scanned": 0,
        "kept": 0,
        "removed": 0,
        "moved": 0,
        "errors": 0,
        "dedup_by": "hash+stem+text",
    }
    if not target_dir.exists():
        return stats
    duplicates_dir = target_dir / "duplicates"
    seen_hash: Dict[str, Path] = {}
    seen_stem: Dict[str, Path] = {}
    seen_text: Dict[str, Path] = {} if HAVE_PYMUPDF else {}
    for pdf in iter_invoice_pdfs(target_dir):
        stats["scanned"] += 1
        try:
            digest = hash_file(pdf)
            stem = stem_key(pdf)
            tfp = text_fingerprint(pdf)
        except Exception:
            stats["errors"] += 1
            continue
        is_dup = False
        if digest in seen_hash or stem in seen_stem:
            is_dup = True
        if tfp and tfp in seen_text:
            is_dup = True
        if not is_dup:
            seen_hash[digest] = pdf
            seen_stem[stem] = pdf
            if tfp:
                seen_text[tfp] = pdf
            stats["kept"] += 1
            continue
        # Duplicate: move into duplicates/ (skip if something already there)
        duplicates_dir.mkdir(parents=True, exist_ok=True)
        dest = ensure_unique(duplicates_dir, pdf.name)
        try:
            shutil.move(str(pdf), dest)
            stats["moved"] += 1
        except Exception:
            stats["errors"] += 1
    stats["removed"] = stats["moved"]
    return stats


def build_runs(
    providers: List[str],
    python_bin: str,
    start_date: str,
    end_date: str,
    base_dir: Path,
    month_label: str,
    graph_client_id: str | None,
    gmail_extra_args: str,
    graph_extra_args: str,
) -> List[ProviderRun]:
    runs: List[ProviderRun] = []
    if "gmail" in providers:
        gmail_dir = base_dir / f"invoices_gmail_{month_label}"
        cmd = [
            python_bin,
            "-m",
            "invplatform.cli.gmail_invoice_finder",
            "--start-date",
            start_date,
            "--end-date",
            end_date,
            "--invoices-dir",
            str(gmail_dir),
            "--download-report",
            str(gmail_dir / "download_report_gmail.json"),
            "--save-json",
            str(gmail_dir / "invoices_gmail.json"),
            "--save-csv",
            str(gmail_dir / "invoices_gmail.csv"),
        ]
        if gmail_extra_args:
            cmd.extend(shlex.split(gmail_extra_args))
        runs.append(ProviderRun(name="gmail", invoices_dir=gmail_dir, command=cmd))
    if "outlook" in providers:
        if not graph_client_id:
            raise SystemExit(
                "GRAPH_CLIENT_ID is required for Outlook/Graph runs "
                "(pass via --graph-client-id or env var)."
            )
        graph_dir = base_dir / f"invoices_outlook_{month_label}"
        cmd = [
            python_bin,
            "-m",
            "invplatform.cli.graph_invoice_finder",
            "--client-id",
            graph_client_id,
            "--authority",
            os.environ.get("GRAPH_AUTHORITY", "consumers"),
            "--start-date",
            start_date,
            "--end-date",
            end_date,
            "--invoices-dir",
            str(graph_dir),
            "--download-report",
            str(graph_dir / "download_report_outlook.json"),
            "--save-json",
            str(graph_dir / "invoices_outlook.json"),
            "--save-csv",
            str(graph_dir / "invoices_outlook.csv"),
        ]
        if graph_extra_args:
            cmd.extend(shlex.split(graph_extra_args))
        runs.append(ProviderRun(name="outlook", invoices_dir=graph_dir, command=cmd))
    return runs


def run_provider(run: ProviderRun) -> ProviderResult:
    env = os.environ.copy()
    env["PYTHONPATH"] = merged_pythonpath(PROJECT_SRC, env.get("PYTHONPATH"))
    run.invoices_dir.mkdir(parents=True, exist_ok=True)
    print(f"[{run.name}] running: {' '.join(run.command)}")
    proc = subprocess.run(run.command, cwd=REPO_ROOT, env=env)
    print(f"[{run.name}] finished with code {proc.returncode}")
    return ProviderResult(
        name=run.name,
        invoices_dir=run.invoices_dir,
        command=run.command,
        returncode=proc.returncode,
    )


def run_all(runs: List[ProviderRun], parallel: bool = True) -> List[ProviderResult]:
    if not runs:
        return []
    if parallel and len(runs) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(runs)) as pool:
            futures = [pool.submit(run_provider, r) for r in runs]
            return [f.result() for f in futures]
    return [run_provider(r) for r in runs]


def write_summary(
    dest_dir: Path,
    start_date: str,
    end_date: str,
    label: str,
    results: List[ProviderResult],
    consolidation: Dict[str, int],
    dedupe: Dict[str, Dict[str, int]],
) -> None:
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "label": label,
        "consolidated_dir": str(dest_dir),
        "providers": {
            r.name: {
                "invoices_dir": str(r.invoices_dir),
                "returncode": r.returncode,
                "command": " ".join(r.command),
            }
            for r in results
        },
        "consolidation": consolidation,
        "deduplication": dedupe,
    }
    dest_dir.mkdir(parents=True, exist_ok=True)
    manifest = dest_dir / "run_summary.json"
    manifest.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[summary] wrote {manifest}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Run Gmail/Outlook invoice fetchers for the current month and consolidate PDFs."
    )
    ap.add_argument(
        "--providers",
        default="gmail,outlook",
        help="Comma-separated providers to run (gmail,outlook). Default: both.",
    )
    ap.add_argument("--month", type=int, help="Target month (1-12). Default: current month.")
    ap.add_argument("--year", type=int, help="Target year. Default: current year.")
    ap.add_argument("--base-dir", default="invoices", help="Root directory for outputs.")
    ap.add_argument(
        "--python", dest="python_bin", default=DEFAULT_PYTHON, help="Python executable to use."
    )
    ap.add_argument(
        "--gmail-extra-args",
        default=os.environ.get("MONTHLY_GMAIL_ARGS", ""),
        help="Extra args forwarded to gmail_invoice_finder.",
    )
    ap.add_argument(
        "--graph-extra-args",
        default=os.environ.get("MONTHLY_GRAPH_ARGS", ""),
        help="Extra args forwarded to graph_invoice_finder.",
    )
    ap.add_argument(
        "--graph-client-id",
        default=os.environ.get("GRAPH_CLIENT_ID"),
        help="Client ID for Outlook/Graph (required when running outlook).",
    )
    ap.add_argument(
        "--sequential",
        action="store_true",
        help="Run providers sequentially instead of in parallel.",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    start_date, end_date, month_label = month_window(args.year, args.month)
    base_dir = Path(args.base_dir).expanduser()
    providers = normalize_providers(args.providers)
    runs = build_runs(
        providers=providers,
        python_bin=args.python_bin,
        start_date=start_date,
        end_date=end_date,
        base_dir=base_dir,
        month_label=month_label,
        graph_client_id=args.graph_client_id,
        gmail_extra_args=args.gmail_extra_args,
        graph_extra_args=args.graph_extra_args,
    )
    if not runs:
        print("No providers requested; nothing to do.")
        return
    print(
        f"Running providers {providers} for {month_label} "
        f"({start_date} -> {end_date}, base={base_dir})"
    )
    results = run_all(runs, parallel=not args.sequential)
    # Deduplicate inside each successful provider directory before consolidation.
    dedupe_stats: Dict[str, Dict[str, int]] = {}
    for r in results:
        if r.returncode == 0:
            dedupe_stats[r.name] = dedupe_provider_dir(r.invoices_dir)
    consolidated_dir = base_dir / f"invoices_{month_label}"
    successful_dirs = [r.invoices_dir for r in results if r.returncode == 0]
    consolidation_stats = consolidate_pdfs(consolidated_dir, successful_dirs)
    write_summary(
        consolidated_dir,
        start_date,
        end_date,
        month_label,
        results,
        consolidation_stats,
        dedupe_stats,
    )
    failures = [r for r in results if r.returncode != 0]
    if failures:
        names = ", ".join(r.name for r in failures)
        raise SystemExit(f"Some providers failed: {names}")


if __name__ == "__main__":
    main()
