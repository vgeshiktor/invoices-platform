#!/usr/bin/env python

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKERS_SRC = ROOT / "apps" / "workers-py" / "src"
if str(WORKERS_SRC) not in sys.path:
    sys.path.insert(0, str(WORKERS_SRC))

from invplatform.cli import monthly_invoices as monthly


DEFAULT_FIXTURE = ROOT / ".ai" / "evals" / "fixtures" / "cross-provider-dedup"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate cross-provider deduplication.")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--work-dir", default=None)
    return parser.parse_args()


def copy_fixture_tree(src: Path, dest: Path) -> None:
    shutil.copytree(src, dest)


def main() -> int:
    args = parse_args()
    fixture_root = Path(args.fixture).expanduser().resolve()
    if not fixture_root.exists():
        raise SystemExit(f"Fixture not found: {fixture_root}")

    base_work_dir = (
        Path(args.work_dir).expanduser().resolve()
        if args.work_dir
        else Path(tempfile.mkdtemp(prefix="eval-cross-provider-dedup-"))
    )
    base_work_dir.mkdir(parents=True, exist_ok=True)

    staged_root = base_work_dir / "staged"
    gmail_src = staged_root / "gmail"
    outlook_src = staged_root / "outlook"
    dest_dir = base_work_dir / "monthly"

    copy_fixture_tree(fixture_root / "gmail", gmail_src)
    copy_fixture_tree(fixture_root / "outlook", outlook_src)

    stats = monthly.consolidate_pdfs(dest_dir, [gmail_src, outlook_src])
    invoice_count = len(list(dest_dir.glob("*.pdf")))
    duplicate_count = int(stats.get("duplicates", 0))

    forbidden_violations = []
    status = "pass" if invoice_count == 1 and duplicate_count == 1 else "fail"

    payload = {
        "task_id": "cross-provider-dedup",
        "status": status,
        "invoice_count": invoice_count,
        "duplicate_count": duplicate_count,
        "forbidden_violations": forbidden_violations,
        "work_dir": str(base_work_dir),
    }
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
