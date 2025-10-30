"""File-system helpers used across invoice discovery flows."""

from __future__ import annotations

import hashlib
import os
import pathlib
import re
from typing import Optional


def ensure_dir(path: str) -> str:
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str, default: str = "invoice.pdf") -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "_", (name or "").strip())
    return name or default


def short_msg_tag(msg_id: str, n: int = 8) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", msg_id or "")
    return (cleaned[-n:] if len(cleaned) >= n else cleaned) or "msg"


def ensure_unique_path(base_dir: str, wanted_name: str, tag: Optional[str] = None) -> str:
    wanted_name = sanitize_filename(wanted_name)
    stem, ext = os.path.splitext(wanted_name)
    if not ext:
        ext = ".pdf"
    if tag:
        stem = f"{stem}__{tag}"
    candidate = os.path.join(base_dir, f"{stem}{ext}")
    i = 2
    while os.path.exists(candidate):
        candidate = os.path.join(base_dir, f"{stem}__{i}{ext}")
        i += 1
    return candidate


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()
