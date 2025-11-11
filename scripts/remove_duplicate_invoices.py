#!/usr/bin/env python3
"""
remove_duplicate_invoices.py
============================

Utility script to deduplicate invoice files (typically PDFs) under a target
directory by comparing SHA-256 hashes. By default it runs in dry-run mode and
prints what would be removed. Use --apply to actually delete or --move-to to
relocate duplicates into a quarantine directory for manual review.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def hash_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """Return SHA-256 digest for path."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def iter_invoice_files(root: Path, exts: Iterable[str]) -> Iterable[Path]:
    """Yield invoice files under root that match the wanted extensions."""
    wanted = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if wanted and path.suffix.lower() not in wanted:
            continue
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


def plan_dedup(root: Path, exts: Iterable[str]) -> Tuple[List[Tuple[Path, Path]], int]:
    """Return list of duplicates (path, kept_path) and total scanned."""
    seen: Dict[str, Path] = {}
    duplicates: List[Tuple[Path, Path]] = []
    count = 0
    for path in iter_invoice_files(root, exts):
        count += 1
        digest = hash_file(path)
        keeper = seen.get(digest)
        if keeper is None:
            seen[digest] = path
        else:
            duplicates.append((path, keeper))
    return duplicates, count


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Remove duplicate invoice files by content hash."
    )
    ap.add_argument("root", type=Path, help="Directory to scan (recursively).")
    ap.add_argument(
        "--ext",
        dest="extensions",
        action="append",
        default=[".pdf"],
        help="File extension to include (default: .pdf). Repeat to add more.",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete/move duplicates. Without this flag the script only reports.",
    )
    ap.add_argument(
        "--move-to",
        dest="move_to",
        type=Path,
        default=None,
        help="Optional directory to move duplicates into instead of deleting them.",
    )

    args = ap.parse_args()
    root: Path = args.root.expanduser().resolve()
    if not root.exists():
        print(f"Root directory not found: {root}", file=sys.stderr)
        sys.exit(2)

    duplicates, total = plan_dedup(root, args.extensions)
    if not duplicates:
        print(f"No duplicates found in {root} (scanned {total} files).")
        return

    print(f"Scanned {total} files under {root}. Found {len(duplicates)} duplicates:")
    for dup, keeper in duplicates:
        print(f"  DUP {dup} -> KEEP {keeper}")

    if not args.apply:
        print("\nDry run only. Re-run with --apply to remove duplicates.")
        return

    removed = 0
    for dup, keeper in duplicates:
        try:
            if args.move_to:
                dest = ensure_unique(args.move_to.expanduser().resolve(), dup.name)
                shutil.move(str(dup), dest)
                action = f"moved to {dest}"
            else:
                dup.unlink()
                action = "deleted"
            removed += 1
            print(f"[dedup] {dup} ({action}); kept {keeper}")
        except Exception as exc:  # pragma: no cover - filesystem errors
            print(f"[dedup][ERROR] {dup}: {exc}", file=sys.stderr)

    print(f"\nDone. Removed {removed} duplicates out of {len(duplicates)} detected.")


if __name__ == "__main__":
    main()
