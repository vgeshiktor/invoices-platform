"""Keyword-based relevance helpers shared across invoice fetchers."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, Tuple
from urllib.parse import urlparse

from . import constants

_KEYWORD_PATTERNS: Dict[Tuple[str, bool], re.Pattern] = {}


def keyword_in_text(text: str, term: str, ignore_case: bool = False) -> bool:
    if not text or not term:
        return False
    key = (term, ignore_case)
    pattern = _KEYWORD_PATTERNS.get(key)
    if pattern is None:
        flags = re.UNICODE
        if ignore_case:
            flags |= re.IGNORECASE
        pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", flags)
        _KEYWORD_PATTERNS[key] = pattern
    return bool(pattern.search(text))


@lru_cache(maxsize=512)
def is_municipal_text(text: str) -> bool:
    return any(k in (text or "") for k in constants.HEB_MUNICIPAL)


def body_has_negative(text: str) -> bool:
    lowered = (text or "").lower()
    return any(k in (text or "") for k in constants.HEB_NEG) or any(
        k in lowered for k in constants.EN_NEG
    )


def body_has_positive(text: str) -> bool:
    lowered = (text or "").lower()
    return any(k in (text or "") for k in constants.HEB_POS) or any(
        k in lowered for k in constants.EN_POS
    )


def should_consider_message(subject: str, preview: str) -> bool:
    text = f"{subject or ''} {preview or ''}"
    if body_has_negative(text):
        return False
    return body_has_positive(text) or is_municipal_text(text)


def within_domain(url: str, domains: list[str]) -> bool:
    try:
        host = urlparse(url).hostname or ""
        return any(host.endswith(d) for d in domains)
    except Exception:
        return False
