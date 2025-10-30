"""PDF inspection helpers shared across invoice fetchers."""

from __future__ import annotations

from typing import Dict

from . import constants
from .relevance import keyword_in_text

try:  # pragma: no cover - optional dependency
    import fitz  # type: ignore

    HAVE_PYMUPDF = True
except Exception:  # pragma: no cover - optional dependency
    HAVE_PYMUPDF = False


def pdf_keyword_stats(path: str) -> Dict:
    """Scan a PDF for positive/negative keyword hits."""
    stats = {"pos_hits": 0, "neg_hits": 0, "pos_terms": [], "neg_terms": []}
    if not HAVE_PYMUPDF:
        return stats
    try:
        doc = fitz.open(path)  # type: ignore[attr-defined]
        for page in doc:
            text = page.get_text("text") or ""
            for term in constants.EN_POS:
                if keyword_in_text(text, term, ignore_case=True):
                    stats["pos_hits"] += 1
                    stats["pos_terms"].append(term)
            for term in constants.HEB_POS:
                if keyword_in_text(text, term):
                    stats["pos_hits"] += 1
                    stats["pos_terms"].append(term)
            for term in constants.EN_NEG:
                if keyword_in_text(text, term, ignore_case=True):
                    stats["neg_hits"] += 1
                    stats["neg_terms"].append(term)
            for term in constants.HEB_NEG:
                if keyword_in_text(text, term):
                    stats["neg_hits"] += 1
                    stats["neg_terms"].append(term)
            if stats["pos_hits"] >= 3 or stats["neg_hits"] >= 1:
                break
    except Exception:
        pass
    return stats


def pdf_confidence(stats: Dict) -> float:
    pos = int(stats.get("pos_hits", 0) or 0)
    neg = int(stats.get("neg_hits", 0) or 0)
    total = pos + neg
    if total <= 0:
        return 1.0 if pos > 0 else 0.0
    return pos / total
