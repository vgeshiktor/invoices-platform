"""PDF inspection helpers shared across invoice fetchers."""

from __future__ import annotations

import hashlib
import re
from typing import Dict, Optional

from . import constants
from .relevance import keyword_in_text

try:  # pragma: no cover - optional dependency
    import fitz  # type: ignore

    HAVE_PYMUPDF = True
except Exception:  # pragma: no cover - optional dependency
    HAVE_PYMUPDF = False


STRONG_POS = set(constants.EN_POS + constants.HEB_POS) - {"חשבונית"}
WEAK_POS = {"חשבונית"}


def text_has_amount_hint(text: str) -> bool:
    """Heuristic: detect currency markers or numbers with cents."""
    if not text:
        return False
    if any(sym in text for sym in ["₪", "$", "€", 'ש"ח', "שח", "ILS", "NIS", "USD", "EUR"]):
        return True
    amount_patterns = [
        r"\b\d{1,3}(?:[.,]\d{3})+[.,]\d{2}\b",  # 1,234.56 or 1.234,56
        r"\b\d+[.,]\d{2}\b",  # 123.45
    ]
    for pat in amount_patterns:
        if re.search(pat, text):
            return True
    return False


def text_has_invoice_id(text: str) -> bool:
    """Heuristic: detect invoice/receipt identifiers."""
    if not text:
        return False
    patterns = [
        r"מס.?ר\s*חשבונית",
        r"חשבונית\s*מס.?ר",
        r"מס.?ר\s*קבלה",
        r"receipt\s*(no|#)",
        r"invoice\s*(no|#)",
    ]
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            return True
    return False


def text_fingerprint(path: str, max_chars: int = 20000) -> Optional[str]:
    """Return a normalized text fingerprint for PDF content (sha256), if possible."""
    if not HAVE_PYMUPDF:
        return None
    try:
        doc = fitz.open(path)  # type: ignore[attr-defined]
        chunks = []
        total = 0
        for page in doc:
            txt = page.get_text("text") or ""
            if not txt:
                continue
            chunks.append(txt)
            total += len(txt)
            if total >= max_chars:
                break
        if not chunks:
            return None
        norm = " ".join(chunks)
        norm = re.sub(r"\s+", " ", norm).strip()
        if not norm:
            return None
        digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()
        return digest
    except Exception:
        return None


def pdf_keyword_stats(path: str) -> Dict:
    """Scan a PDF for positive/negative keyword hits plus amount/invoice hints."""
    stats = {
        "pos_hits": 0,
        "neg_hits": 0,
        "pos_terms": [],
        "neg_terms": [],
        "strong_hits": 0,
        "weak_hits": 0,
        "amount_hint": None,
        "invoice_id_hint": None,
    }
    if not HAVE_PYMUPDF:
        return stats
    try:
        doc = fitz.open(path)  # type: ignore[attr-defined]
        for page in doc:
            text = page.get_text("text") or ""
            # Keywords
            for term in constants.EN_POS:
                if keyword_in_text(text, term, ignore_case=True):
                    stats["pos_hits"] += 1
                    stats["pos_terms"].append(term)
                    if term in STRONG_POS:
                        stats["strong_hits"] += 1
                    elif term in WEAK_POS:
                        stats["weak_hits"] += 1
            for term in constants.HEB_POS:
                if keyword_in_text(text, term):
                    stats["pos_hits"] += 1
                    stats["pos_terms"].append(term)
                    if term in STRONG_POS:
                        stats["strong_hits"] += 1
                    elif term in WEAK_POS:
                        stats["weak_hits"] += 1
            for term in constants.EN_NEG:
                if keyword_in_text(text, term, ignore_case=True):
                    stats["neg_hits"] += 1
                    stats["neg_terms"].append(term)
            for term in constants.HEB_NEG:
                if keyword_in_text(text, term):
                    stats["neg_hits"] += 1
                    stats["neg_terms"].append(term)
            # Amount / invoice id hints
            if stats["amount_hint"] is None:
                stats["amount_hint"] = text_has_amount_hint(text)
            if stats["invoice_id_hint"] is None:
                stats["invoice_id_hint"] = text_has_invoice_id(text)
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
