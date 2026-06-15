#!/usr/bin/env python

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = [
    ROOT / "reports",
    ROOT
    / "docs"
    / "superpowers"
    / "artifacts"
    / "2026-05-20-invoice-review-command-center",
]
TEXT_SUFFIXES = {".csv", ".json", ".md", ".txt", ".yaml", ".yml"}
SECRET_PATTERNS = {
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-pat": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "openai-key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "pem-private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
}


def iter_scan_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                files.append(path)
    return files


def main() -> None:
    findings: list[str] = []
    for path in iter_scan_files():
        text = path.read_text(encoding="utf-8")
        for label, pattern in SECRET_PATTERNS.items():
            match = pattern.search(text)
            if match:
                findings.append(f"{path.relative_to(ROOT)}: {label}")

    if findings:
        raise SystemExit(
            "secret-like content found in generated artifacts:\n" + "\n".join(findings)
        )


if __name__ == "__main__":
    main()
