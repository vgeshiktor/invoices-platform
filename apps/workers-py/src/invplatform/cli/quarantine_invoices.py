#!/usr/bin/env python3
"""
Scan a directory tree for PDFs and move non-invoice files into quarantine/.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Dict, Iterable, Tuple

from invplatform.domain import pdf as domain_pdf


SKIP_DIRS = {"_tmp", "quarantine", "duplicates"}
HAVE_PYMUPDF = getattr(domain_pdf, "HAVE_PYMUPDF", False)


def iter_pdfs(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    for path in root.rglob("*.pdf"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def ensure_unique(dest_dir: Path, name: str) -> Path:
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


def assess_pdf(path: Path) -> Tuple[bool, Dict]:
    stats = domain_pdf.pdf_keyword_stats(str(path))
    pos_hits = stats.get("pos_hits", 0) or 0
    neg_hits = stats.get("neg_hits", 0) or 0
    strong_hits = stats.get("strong_hits", pos_hits) or 0
    amount_hint = stats.get("amount_hint")
    invoice_id_hint = stats.get("invoice_id_hint")
    weak_only = pos_hits > 0 and strong_hits == 0

    ok = pos_hits >= 1 and neg_hits == 0
    if ok and weak_only:
        if HAVE_PYMUPDF:
            ok = bool(amount_hint or invoice_id_hint)
    return ok, stats


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Move PDFs that fail invoice heuristics into quarantine/."
    )
    ap.add_argument(
        "--input-dir",
        default="invoices",
        help="Root directory containing invoice PDFs (default: invoices).",
    )
    ap.add_argument(
        "--quarantine-dir",
        help="Destination quarantine directory (default: <input-dir>/quarantine).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be moved.",
    )
    return ap.parse_args()


def main() -> None:
    if not HAVE_PYMUPDF:
        raise SystemExit("PyMuPDF is required to inspect PDFs (pip install pymupdf).")
    args = parse_args()
    root = Path(args.input_dir).expanduser()
    quarantine_dir = (
        Path(args.quarantine_dir).expanduser() if args.quarantine_dir else root / "quarantine"
    )
    moved = 0
    scanned = 0
    for pdf in iter_pdfs(root):
        scanned += 1
        ok, stats = assess_pdf(pdf)
        if ok:
            continue
        if args.dry_run:
            print(f"[DRY] {pdf} -> {quarantine_dir} ({stats})")
            moved += 1
            continue
        dest = ensure_unique(quarantine_dir, pdf.name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(pdf), str(dest))
        moved += 1
        print(f"[MOVE] {pdf} -> {dest}")
    print(f"Scanned {scanned} PDFs, quarantined {moved}.")


if __name__ == "__main__":
    main()
