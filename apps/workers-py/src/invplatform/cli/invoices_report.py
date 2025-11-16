from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from pdfminer.high_level import extract_text
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise SystemExit(
        "Missing dependency: pdfminer.six is required for invoice parsing. "
        "Install it with `pip install pdfminer.six` or add it to your environment."
    ) from exc

try:
    import fitz

    HAVE_PYMUPDF = True
except ModuleNotFoundError:
    HAVE_PYMUPDF = False


Amount = Optional[float]

KNOWN_VENDOR_MARKERS: Tuple[Tuple[str, str], ...] = (
    ("יול ימר", "רמי לוי תקשורת"),
    ("פרטנר", 'חברת פרטנר תקשורת בע"מ'),
    ("רנטרפ", 'חברת פרטנר תקשורת בע"מ'),
    ("partner communications", 'חברת פרטנר תקשורת בע"מ'),
)

PETAH_TIKVA_KEYWORDS: Tuple[str, ...] = ("פתח תק", "הווקת חתפ")
PETAH_TIKVA_MUNICIPAL_MARKERS: Tuple[str, ...] = (
    "עיריית",
    "עריית",
    "עירייה",
    "עיריה",
    "ערייה",
    "עריה",
    "עירית",
    "ערית",
    "העירייה",
    "העיריה",
    "תיעיר",
    "תיעירת",
    "רשות מקומית",
)

PUBLIC_TRANSPORT_HEBREW_MARKERS: Tuple[str, ...] = (
    "תירוביצ הרובחת",
    "תירוביצה הרובחת",
    "תירוביצה הרובחתה",
    "התחבורה הציבורית",
    "וק-בר",
    "רב-קו",
)
PUBLIC_TRANSPORT_LATIN_MARKERS: Tuple[str, ...] = (
    "ravpass",
    "rav-kav",
    "ravkav",
    "rav kav",
)
PUBLIC_TRANSPORT_INVOICE_FOR = "רב-קו - טעינה"


@dataclass
class InvoiceRecord:
    source_file: str
    invoice_id: Optional[str] = None
    invoice_date: Optional[str] = None
    invoice_from: Optional[str] = None
    invoice_for: Optional[str] = None
    invoice_total: Amount = None
    invoice_vat: Amount = None
    currency: Optional[str] = "₪"
    notes: Optional[str] = None
    breakdown_sum: Amount = None
    breakdown_values: Optional[List[float]] = None
    base_before_vat: Amount = None
    vat_rate: Optional[float] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    period_label: Optional[str] = None
    due_date: Optional[str] = None
    category: Optional[str] = None
    category_confidence: Optional[float] = None
    category_rule: Optional[str] = None
    reference_numbers: Optional[List[str]] = None
    data_source: Optional[str] = None
    parse_confidence: Optional[float] = None
    municipal: Optional[bool] = None
    duplicate_hash: Optional[str] = None

    def to_csv_row(self, fields: Sequence[str]) -> List[str]:
        row = []
        data = asdict(self)
        for field in fields:
            value = data.get(field)
            if isinstance(value, float):
                row.append(f"{value:.2f}")
            elif isinstance(value, bool):
                row.append("true" if value else "false")
            elif isinstance(value, (list, dict)):
                row.append(json.dumps(value, ensure_ascii=False))
            elif value is None:
                row.append("")
            else:
                row.append(str(value))
        return row


def normalize_amount_token(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    sign = ""
    stripped = raw.strip()
    if stripped.startswith("-"):
        sign = "-"
    token = "".join(ch for ch in raw if ch.isdigit() or ch in ".,")
    if not token:
        return None
    body = token.lstrip("-")
    if re.match(r"^\d+\.\d{3}$", body):
        head, tail = body.split(".")
        if len(head) <= 2:
            swapped = tail + "." + head
        else:
            swapped = body[::-1]
        token = ("-" if token.startswith("-") else "") + swapped
    if "," in token and "." in token:
        token = token.replace(",", "")
    elif token.count(",") > 1:
        token = token.replace(",", "")
    elif token.count(",") == 1 and "." not in token:
        token = token.replace(",", ".")
    return sign + token


def parse_number(raw: Optional[str]) -> Amount:
    token = normalize_amount_token(raw)
    if not token:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def select_amount(tokens: Iterable[str]) -> Amount:
    candidates = []
    for token in tokens:
        normalized = normalize_amount_token(token)
        if not normalized:
            continue
        if normalized.isdigit() and len(normalized) == 4 and normalized.startswith("20"):
            continue
        try:
            amount = float(normalized)
        except ValueError:
            continue
        candidates.append((amount, normalized))
    if not candidates:
        return None
    for amount, normalized in candidates:
        if "." in normalized and len(normalized.split(".")[-1]) == 2:
            return amount
    for amount, normalized in candidates:
        if "." in normalized:
            return amount
    for amount, _ in candidates:
        if amount >= 10:
            return amount
    return candidates[0][0]


MONTH_NAME_MAP = {
    "ינואר": 1,
    "פברואר": 2,
    "מרץ": 3,
    "מרס": 3,
    "אפריל": 4,
    "מאי": 5,
    "יוני": 6,
    "יולי": 7,
    "אוגוסט": 8,
    "ספטמבר": 9,
    "ספטמבער": 9,
    "אוקטובר": 10,
    "נובמבר": 11,
    "דצמבר": 12,
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

MONTH_LABELS_HE = {
    1: "ינואר",
    2: "פברואר",
    3: "מרץ",
    4: "אפריל",
    5: "מאי",
    6: "יוני",
    7: "יולי",
    8: "אוגוסט",
    9: "ספטמבר",
    10: "אוקטובר",
    11: "נובמבר",
    12: "דצמבר",
}


def normalize_date_token(token: str, default_day: Optional[int] = None) -> Optional[str]:
    if not token:
        return None
    candidate = (
        token.strip().replace("\\", "-").replace("/", "-").replace(".", "-").replace(",", "-")
    )
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y", "%m-%d-%Y", "%d-%b-%Y", "%d-%b-%y"):
        try:
            dt = datetime.strptime(candidate, fmt)
            if dt.year < 100:
                dt = dt.replace(year=2000 + dt.year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # month-year patterns
    m = re.match(r"(\d{4})-(\d{1,2})$", candidate)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = default_day or 1
        day = min(day, calendar.monthrange(year, month)[1])
        return date(year, month, day).strftime("%Y-%m-%d")
    m = re.match(r"(\d{1,2})-(\d{4})$", candidate)
    if m:
        month = int(m.group(1))
        year = int(m.group(2))
        day = default_day or 1
        day = min(day, calendar.monthrange(year, month)[1])
        return date(year, month, day).strftime("%Y-%m-%d")
    lowered = candidate.lower()
    parts = lowered.split()
    if len(parts) == 2 and parts[0] in MONTH_NAME_MAP and parts[1].isdigit():
        month = MONTH_NAME_MAP[parts[0]]
        year = int(parts[1])
        day = default_day or 1
        day = min(day, calendar.monthrange(year, month)[1])
        return date(year, month, day).strftime("%Y-%m-%d")
    return None


def extract_period_info(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not text:
        return None, None, None
    autopay_segment = None
    autopay_match = re.search(r"((?:\d{2}/\d{2}/\d{4}).{0,40}?){2,}הוראת הקבע", text)
    if autopay_match:
        autopay_segment = autopay_match.group(0)
    if autopay_segment:
        date_tokens = re.findall(r"\d{2}/\d{2}/\d{4}", autopay_segment)
        if len(date_tokens) >= 2:
            parsed_dates = []
            for token in date_tokens:
                normalized = normalize_date_token(token)
                if normalized:
                    parsed_dates.append(datetime.strptime(normalized, "%Y-%m-%d").date())
            if len(parsed_dates) >= 2:
                parsed_dates.sort()
                start_base = parsed_dates[0]
                end_autopay = parsed_dates[-1]
                start = start_base.replace(day=1)
                end = end_autopay - timedelta(days=1)
                if end < start:
                    end = end_autopay
                start_label = MONTH_LABELS_HE.get(start.month, start.strftime("%B"))
                end_label = MONTH_LABELS_HE.get(end.month, end.strftime("%B"))
                label = f"{start_label} - {end_label}"
                return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), label
    range_pattern = re.search(
        r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\s*[-–]\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        text,
    )
    if range_pattern:
        start = normalize_date_token(range_pattern.group(1))
        end = normalize_date_token(range_pattern.group(2))
        label = f"{start} - {end}" if start and end else None
        return start, end, label
    bilingual_pattern = re.search(r"(\d{4})\s+([א-ת]+)\s*[-–]\s*([א-ת]+)", text)
    if bilingual_pattern:
        year = int(bilingual_pattern.group(1))
        month_a = MONTH_NAME_MAP.get(bilingual_pattern.group(2).lower())
        month_b = MONTH_NAME_MAP.get(bilingual_pattern.group(3).lower())
        if month_a and month_b:
            start = date(year, month_a, 1)
            end = date(year, month_b, calendar.monthrange(year, month_b)[1])
            label = f"{bilingual_pattern.group(3)} - {bilingual_pattern.group(2)}"
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), label
    month_year_pattern = re.search(
        r"(?:תקופה|billing|statement|month|חודש)\D*([A-Za-zא-ת]+)\s+(\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if month_year_pattern:
        month_name = month_year_pattern.group(1).lower()
        year = int(month_year_pattern.group(2))
        month = MONTH_NAME_MAP.get(month_name)
        if month:
            start_date = date(year, month, 1)
            end_date = date(year, month, calendar.monthrange(year, month)[1])
            return (
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                f"{start_date:%Y-%m} ({month_year_pattern.group(1)} {year})",
            )
    return None, None, None
    bilingual_pattern = re.search(r"(\d{4})\s+([א-ת]+)\s*[-–]\s*([א-ת]+)", text)
    if bilingual_pattern:
        year = int(bilingual_pattern.group(1))
        month_a = MONTH_NAME_MAP.get(bilingual_pattern.group(2).lower())
        month_b = MONTH_NAME_MAP.get(bilingual_pattern.group(3).lower())
        if month_a and month_b:
            start = date(year, month_a, 1)
            end = date(year, month_b, calendar.monthrange(year, month_b)[1])
            label = f"{bilingual_pattern.group(2)} - {bilingual_pattern.group(3)}"
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), label


def extract_due_date(text: str) -> Optional[str]:
    if not text:
        return None
    patterns = [
        r"(?:Due Date|Payment Due|לתשלום עד|מועד תשלום|תאריך אחרון לתשלום)\D{0,15}([0-9./-]{6,10})",
        r"מועד אחרון[:\s]+([0-9./-]{6,10})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            normalized = normalize_date_token(match.group(1))
            if normalized:
                return normalized
    return None


def extract_reference_numbers(text: str) -> List[str]:
    if not text:
        return []
    patterns = [
        r"(?:PO|P\.O\.|Purchase Order)[\s#:=-]*([A-Z0-9-]{4,})",
        r"מספר\s+(?:הזמנה|לקוח|חוזה|עסקה)[\s#:=-]*([0-9-]{4,})",
        r"(?:Customer ID|Account Number)[\s#:=-]*([A-Z0-9-]{4,})",
    ]
    refs: List[str] = []
    for pattern in patterns:
        refs.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    seen: Dict[str, bool] = {}
    ordered: List[str] = []
    for ref in refs:
        key = ref.strip()
        if not key or key in seen:
            continue
        seen[key] = True
        ordered.append(key)
        if len(ordered) >= 5:
            break
    return ordered


CATEGORY_RULES: List[Tuple[str, float, List[str], List[str]]] = [
    (
        "transportation",
        0.95,
        [
            "תירוביצ הרובחת",
            "תירוביצה הרובחת",
            "התחבורה הציבורית",
            "רב-קו",
            "וק-בר",
            "ravpass",
            "rav-kav",
            "ravkav",
            "rav kav",
        ],
        [
            "תחבורה ציבורית",
            "ravpass",
            "rav-kav",
            "bus",
            "train",
            "light rail",
            "travel card",
        ],
    ),
    (
        "communication",
        1.0,
        [
            "בזק",
            "bezeq",
            "cellcom",
            "partner",
            "פרטנר",
            "hot",
            "yes",
            "סטינג",
            "stingtv",
            "רמי לוי",
            "רמי לוי תקשורת",
            "rami levy",
            "rami-levy",
        ],
        ["תקשורת", "אינטרנט", "internet", "fiber", "broadband"],
    ),
    (
        "utilities",
        0.9,
        ["חשמל", "חברת החשמל", "מים", "תאגיד מים", "ארנונה", "city", "municipality"],
        ["bill", "utility"],
    ),
    (
        "software_saas",
        0.8,
        ["google", "microsoft", "aws", "stripe", "notion", "slack"],
        ["subscription", "license"],
    ),
    ("finance", 0.7, ["visa", "mastercard", "amex", "isracard"], ["כרטיס אשראי"]),
    ("services", 0.6, [], ["שירות", "service", "support"]),
]


def classify_invoice(
    text: str, supplier: Optional[str], is_municipal: bool
) -> Tuple[Optional[str], Optional[float], Optional[str]]:
    if is_municipal:
        return "municipal_tax", 1.0, "municipal_flag"
    text_lower = (text or "").lower()
    supplier_lower = (supplier or "").lower()
    for category, weight, vendor_keys, keyword_hits in CATEGORY_RULES:
        for vendor_key in vendor_keys:
            if vendor_key.lower() in supplier_lower:
                return category, weight, f"vendor:{vendor_key}"
        for keyword in keyword_hits:
            if keyword.lower() in text_lower:
                return category, weight * 0.85, f"keyword:{keyword}"
    return None, None, None


def compute_parse_confidence(record: InvoiceRecord) -> float:
    confidence = 0.4
    if record.invoice_total is not None:
        confidence += 0.25
    if record.invoice_vat is not None:
        confidence += 0.1
    if record.breakdown_sum and record.invoice_total:
        if abs(record.breakdown_sum - record.invoice_total) <= 1.0:
            confidence += 0.15
    if record.period_start or record.period_end:
        confidence += 0.05
    if record.reference_numbers:
        confidence += 0.05
    if record.category:
        confidence += 0.05
    return min(confidence, 0.99)


def file_sha256(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def configure_pdfminer_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.ERROR
    for name in (
        "pdfminer",
        "pdfminer.pdfinterp",
        "pdfminer.pdfdocument",
        "pdfminer.converter",
        "pdfminer.pdfpage",
    ):
        logging.getLogger(name).setLevel(level)


def amount_near_markers(
    text: str, patterns: Iterable[str], window: int = 120, prefer: str = "max"
) -> Amount:
    def extract_values(tokens: List[str]) -> List[Tuple[float, str]]:
        values: List[Tuple[float, str]] = []
        for tok in tokens:
            amount = parse_number(tok)
            if amount is not None and amount > 0:
                values.append((amount, tok))
        return values

    def choose(values: List[Tuple[float, str]]) -> Amount:
        if not values:
            return None
        decimals = [val for val in values if "." in val[1] or "," in val[1]]
        pool = decimals if decimals else values
        amounts = [val for val, _ in pool]
        if prefer == "min":
            return min(amounts)
        return max(amounts)

    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.MULTILINE):
            tail = text[match.end() : match.end() + window]
            head = text[max(0, match.start() - window) : match.start()]
            values = extract_values(re.findall(r"[\d.,]+", tail))
            values += extract_values(re.findall(r"[\d.,]+", head))
            amount = choose(values)
            if amount is not None:
                return amount
    return None


def needs_fallback_text(text: str) -> bool:
    if not text:
        return True
    stripped = text.strip()
    if len(stripped) < 200:
        return True
    hebrew_letters = len(re.findall(r"[א-ת]", stripped))
    glyph_markers = stripped.count("(cid:")
    return hebrew_letters < 15 or glyph_markers > 5


def extract_text_with_pymupdf(path: Path) -> str:
    if not HAVE_PYMUPDF:
        return ""
    try:
        doc = fitz.open(path)
    except Exception:
        return ""
    parts: List[str] = []
    try:
        for page in doc:
            try:
                parts.append(page.get_text("text"))
            except Exception:
                continue
    finally:
        doc.close()
    return "\n".join(parts)


def extract_lines(text: str) -> List[str]:
    cleaned = text.replace("\r", "\n")
    raw_lines = [ln.strip() for ln in cleaned.splitlines()]
    raw_lines = [ln for ln in raw_lines if ln]

    def is_basic_number(token: str) -> bool:
        return bool(re.fullmatch(r"-?\d+", token))

    merged: List[str] = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if line == "." and merged and i + 1 < len(raw_lines):
            prev = merged.pop()
            nxt = raw_lines[i + 1]
            if is_basic_number(prev) and is_basic_number(nxt):
                merged.append(f"{nxt}.{prev}")
                i += 2
                continue
            merged.append(prev)
        elif line.endswith(".") and line != "." and line.count(".") == 1:
            body = line[:-1]
            if is_basic_number(body):
                combined = False
                if merged:
                    prev = merged[-1]
                    if is_basic_number(prev):
                        merged[-1] = f"{prev}.{body}"
                        i += 1
                        combined = True
                if combined:
                    continue
                if i + 1 < len(raw_lines):
                    nxt = raw_lines[i + 1]
                    if is_basic_number(nxt):
                        merged.append(f"{nxt}.{body}")
                        i += 2
                        continue
        merged.append(line)
        i += 1

    return [ln for ln in merged if ln]


def search_patterns(patterns: Iterable[str], text: str) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def normalize_invoice_for_value(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    cleaned = raw.strip().strip(":\"'").strip()
    cleaned = re.sub(r"^[\d\s'\"`.,-]+", "", cleaned)
    cleaned = cleaned.strip()
    if not cleaned or not re.search(r"[A-Za-zא-ת]", cleaned):
        return None
    match = re.search(r"מס-?\s*(\d{4})\s+([א-תA-Za-z\s\"']{2,})", cleaned)
    if match:
        desc = match.group(2).strip()
        year = match.group(1)
        if desc:
            cleaned = f"{desc} {year}"
    if "ארנונה לעסקים" in cleaned:
        return "ארנונה לעסקים"
    if "ארנונה" in cleaned:
        return "ארנונה"
    return cleaned or None


def infer_invoice_id(lines: List[str], text: str) -> Optional[str]:
    candidates: List[Tuple[int, str]] = []

    if text:
        special_match = re.search(
            r"מס.?['׳]?\s+חשבון\s+תקופתי[:\s-]*([\d-]{6,})",
            text,
            flags=re.MULTILINE,
        )
        if special_match:
            cleaned = re.sub(r"\D", "", special_match.group(1))
            if cleaned:
                return cleaned
        period_match = re.search(
            r"([\d-]{6,})[\s\S]{0,80}?[:]?יתפוקת",
            text,
            flags=re.MULTILINE,
        )
        if period_match:
            cleaned = re.sub(r"\D", "", period_match.group(1))
            if cleaned:
                return cleaned

    def add_candidate(value: Optional[str], priority: int) -> None:
        val = (value or "").strip()
        if not val:
            return
        cleaned = re.sub(r"[^\d]", "", val)
        candidates.append((priority, cleaned or val))

    pattern_defs = [
        (r"חשבונית(?:\s+מס)?(?:\s+קבלה)?\s*(?:מספר|No\.?)\s*[:\-]?\s*(\d+)", 0),
        (r"(\d{4,})\s*רפסמ\s*תינובשח", 0),
        (r"(\d{4,})\s*רפסמ\s*קיתב\s*מ\"עמ", 1),
        (r"(\d{4,})\s+רפסמ", 2),
        (r"מספר\s+(\d{4,})", 2),
        (r"מס.?['׳]?\s*מסלקה/שובר/ספח[:\s]+(\d{4,})", 0),
        (r"מסלקה/שובר/ספח[:\s]+(\d{4,})", 1),
    ]
    for pattern, priority in pattern_defs:
        for match in re.finditer(pattern, text):
            add_candidate(match.group(1), priority)

    if not candidates:
        for idx, line in enumerate(lines):
            if "רפסמ" in line:
                digits = re.findall(r"\d[\d/-]*", line)
                for val in digits:
                    add_candidate(val, 3)
                if digits:
                    break
                if idx > 0:
                    prev = re.findall(r"\d[\d/-]*", lines[idx - 1])
                    for val in prev:
                        add_candidate(val, 3)
                    break
    if not candidates:
        for line in lines[:60]:
            for token in re.findall(r"\b\d{8,12}\b", line):
                add_candidate(token, 5)
    if not candidates and text:
        for token in re.findall(r"\b\d{8,12}\b", text):
            add_candidate(token, 6)

    if candidates:
        candidates.sort(key=lambda item: (item[0], -len(item[1]), item[1]))
        return candidates[0][1]
    return None


def infer_invoice_date(text: str) -> Optional[str]:
    patterns = [
        r"(\d{2}/\d{2}/\d{4})\s*:ךיראת",
        r"תאריך\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        r"Date\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        r"תאריך\s*הדפסה\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
    ]
    value = search_patterns(patterns, text)
    if value:
        return value
    match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    if match:
        return match.group(1)
    return None


def detect_known_vendor(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    for marker, label in KNOWN_VENDOR_MARKERS:
        if marker in text:
            return label
    return None


def has_public_transport_marker(text: Optional[str]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if any(marker in text for marker in PUBLIC_TRANSPORT_HEBREW_MARKERS):
        return True
    return any(marker in lowered for marker in PUBLIC_TRANSPORT_LATIN_MARKERS)


def looks_like_petah_tikva_municipality(text: Optional[str]) -> bool:
    if not text:
        return False
    if not any(marker in text for marker in PETAH_TIKVA_KEYWORDS):
        return False
    return any(marker in text for marker in PETAH_TIKVA_MUNICIPAL_MARKERS)


def infer_invoice_from(lines: List[str], text: Optional[str] = None) -> Optional[str]:
    candidate: Optional[str] = None
    for line in lines:
        if 'מ"עב' in line or 'בע"מ' in line or "Ltd" in line or "חברה" in line:
            candidate = line
            break
    if candidate is None:
        for line in lines[:15]:
            if "www" in line or "@" in line or "cid:" in line:
                continue
            if line.isdigit():
                continue
            if re.search(r"[א-תA-Za-z]", line):
                candidate = line
                break
    vendor = detect_known_vendor(text)
    if vendor:
        return vendor
    if text:
        match = re.search(r"ע[יר]יית\s+[^\n]{2,40}", text)
        if match:
            result = match.group(0).strip().replace("עריית", "עיריית")
            return result
        if looks_like_petah_tikva_municipality(text):
            return "עיריית פתח תקווה"
    return candidate


def numeric_candidates(line: str) -> List[tuple[str, bool]]:
    candidates: List[tuple[str, bool]] = []
    for match in re.finditer(r"[\d.,]+", line):
        token = match.group(0)
        start, end = match.start(), match.end()
        before = line[max(0, start - 2) : start]
        after = line[end : end + 2]
        is_percent = "%" in before or "%" in after
        candidates.append((token, is_percent))
    return candidates


def numeric_values_near_marker(lines: List[str], marker: str, window: int = 4) -> List[float]:
    values: List[float] = []
    for idx, line in enumerate(lines):
        if marker in line:
            for token, is_percent in numeric_candidates(line):
                if is_percent:
                    continue
                amount = parse_number(token)
                if amount is not None:
                    values.append(amount)
            for offset in range(1, window + 1):
                for pos in (idx - offset, idx + offset):
                    if 0 <= pos < len(lines):
                        for token, is_percent in numeric_candidates(lines[pos]):
                            if is_percent:
                                continue
                            amount = parse_number(token)
                            if amount is not None:
                                values.append(amount)
            break
    return values


def sum_numeric_block(
    lines: List[str],
    start_markers: Iterable[str],
    end_markers: Iterable[str],
) -> Tuple[Optional[float], List[float]]:
    collecting = False
    total = 0.0
    found = False
    values: List[float] = []
    for line in lines:
        if not collecting and any(marker in line for marker in start_markers):
            collecting = True
            continue
        if collecting:
            if any(end in line for end in end_markers):
                break
            token = line.strip()
            if re.match(r"^-?\d[\d,]*(?:\.\d+)?$", token):
                val = parse_number(token)
                if val is not None:
                    total += val
                    values.append(val)
                    found = True
    return (total if found else None, values)


def extract_partner_invoice_for(lines: List[str], raw_text: Optional[str] = None) -> Optional[str]:
    stop_markers = ['סה"כ', "סהכ", 'כ"הס']
    for idx, line in enumerate(lines):
        if "פירוט" in line and "חיובים" in line and "זיכויים" in line and "החשבון" in line:
            details: List[str] = []
            for lookahead in range(1, 8):
                pos = idx + lookahead
                if pos >= len(lines):
                    break
                candidate = lines[pos].strip()
                if not candidate:
                    continue
                if any(marker in candidate for marker in stop_markers):
                    break
                if re.search(r"[א-תA-Za-z]", candidate):
                    details.append(candidate)
                if len(details) >= 4:
                    break
            if details:
                return " | ".join(details)
            return "פירוט חיובים וזיכויים לתקופת החשבון"

    if raw_text:
        segment_match = re.search(
            r"פירוט\s+חיובים\s+וזיכויים\s+לתקופת\s+החשבון\s+(.*?)\s+סה\"?כ\s+חיובי\s+החשבון",
            raw_text,
            flags=re.DOTALL,
        )
        if segment_match:
            segment = segment_match.group(1)
            entries: List[str] = []
            match_mobile = re.search(r"(\d+)מנויי\s*סלולר", segment)
            if match_mobile:
                entries.append(f"{match_mobile.group(1)} מנויי סלולר")
            match_transport = re.search(r"(\d+)מנוי\s*תמסורת\s*([\d-]+)", segment)
            if match_transport:
                count, ident = match_transport.groups()
                entries.append(f"{count} מנוי תמסורת {ident}")
            if re.search(r"תנועות\s+כלליות\s+בחשבון\s+הלקוח", segment):
                entries.append("תנועות כלליות בחשבון הלקוח")
            if entries:
                return " | ".join(entries)
            return "פירוט חיובים וזיכויים לתקופת החשבון"
    return None


def infer_invoice_for(lines: List[str], text: Optional[str] = None) -> Optional[str]:
    if has_public_transport_marker(text):
        return PUBLIC_TRANSPORT_INVOICE_FOR
    partner_summary = extract_partner_invoice_for(lines, text)
    if partner_summary:
        return partner_summary
    if ":םיטרפ" in " ".join(lines):
        try:
            start = lines.index(":םיטרפ")
        except ValueError:
            start = -1
        if start >= 0:
            collected: List[str] = []
            for ln in lines[start + 1 :]:
                if any(marker in ln for marker in ("טקמ", 'כ"הס', 'סה"כ', "כסה")):
                    break
                if len(ln) > 2:
                    collected.append(ln)
            if collected:
                return " | ".join(collected[:5])
    for idx, line in enumerate(lines):
        if "פירוט החיוב" in line or "פירוט החיובים" in line:
            tail = normalize_invoice_for_value(
                line.split("פירוט החיוב", 1)[-1]
                if "פירוט החיוב" in line
                else line.split("פירוט החיובים", 1)[-1]
            )
            if tail and "נכס" not in tail:
                return tail
            for lookahead in range(1, 8):
                if idx + lookahead < len(lines):
                    raw_line = lines[idx + lookahead].strip()
                    skip_markers = [
                        'סה"כ',
                        "סהכ",
                        "תיאור",
                        "כתובת",
                        "מס' זיהוי",
                        "מספר זיהוי",
                        "מס'",
                    ]
                    if any(marker in raw_line for marker in skip_markers):
                        continue
                    candidate = normalize_invoice_for_value(raw_line)
                    if candidate:
                        return candidate
    for line in lines:
        if " עבור " in line or " - " in line:
            if len(line) < 200:
                if re.search(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}", line):
                    continue
                normalized = normalize_invoice_for_value(line)
                return normalized or line
    if text:
        if "ארנונה לעסקים" in text:
            return "ארנונה לעסקים"
        if "ארנונה" in text:
            return "ארנונה"
    return None


def find_amount_before_marker(
    lines: List[str], marker: str, *, prefer_inline: bool = False
) -> Amount:
    for idx, line in enumerate(lines):
        if marker in line:
            inline_candidates = numeric_candidates(line)
            line_has_percent = "%" in line
            preferred = [tok for tok, is_percent in inline_candidates if not is_percent]
            tokens = preferred if preferred else [tok for tok, _ in inline_candidates]
            if line_has_percent:
                tokens = []
            amount = select_amount(tokens[::-1]) if tokens else None
            if amount is not None:
                return amount
            if prefer_inline:
                continue
            for lookback in range(1, 4):
                if idx - lookback >= 0:
                    candidate = lines[idx - lookback]
                    if not prefer_inline and "/" in candidate and "₪" not in candidate:
                        continue
                    candidate_tokens = numeric_candidates(candidate)
                    preferred_tokens = [
                        tok for tok, is_percent in candidate_tokens if not is_percent
                    ]
                    tokens = (
                        preferred_tokens
                        if preferred_tokens
                        else [tok for tok, _ in candidate_tokens]
                    )
                    amount = select_amount(tokens[::-1]) if tokens else None
                    if amount is not None:
                        return amount
            for lookahead in range(1, 4):
                if idx + lookahead < len(lines):
                    candidate = lines[idx + lookahead]
                    candidate_tokens = numeric_candidates(candidate)
                    preferred_tokens = [
                        tok for tok, is_percent in candidate_tokens if not is_percent
                    ]
                    tokens = (
                        preferred_tokens
                        if preferred_tokens
                        else [tok for tok, _ in candidate_tokens]
                    )
                    amount = select_amount(tokens[::-1]) if tokens else None
                    if amount is not None:
                        return amount
            break
    return None


def vat_rate_estimate(total: Optional[float], vat: Optional[float]) -> Optional[float]:
    if total is None or vat is None or total == 0:
        return None
    base = total - vat
    if base <= 0:
        return None
    return round((vat / base) * 100, 2)


def extract_vat_rate_from_text(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    patterns = [
        r"([\d.,]+)\s*%[^\n]{0,15}?מ\"?עמ",
        r"מ\"?עמ[^%\d]{0,15}?([\d.,]+)\s*%",
        r"VAT[^%\d]{0,15}?([\d.,]+)\s*%",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = parse_number(match.group(1))
            if value is not None:
                return round(value, 2)
    return None


def infer_totals(
    lines: List[str],
    text: str,
    *,
    debug: bool = False,
    label: str = "",
    pdfminer_lines: Optional[List[str]] = None,
) -> Dict[str, object]:
    def dbg(msg: str) -> None:
        if debug:
            prefix = f"[debug][{label}] " if label else "[debug] "
            print(prefix + msg)

    def numbers_after_marker(marker: str, limit: int = 10) -> Tuple[List[float], List[float]]:
        best: List[float] = []
        best_len = 0
        best_max: Optional[float] = None
        aggregated: List[float] = []
        for idx, line in enumerate(lines):
            if marker not in line:
                continue
            collected: List[float] = []
            for offset in range(1, limit + 1):
                pos = idx + offset
                if pos >= len(lines):
                    break
                token = lines[pos]
                if "." not in token and "," not in token and "₪" not in token:
                    if collected:
                        break
                    continue
                value = parse_number(token)
                if value is None:
                    if collected:
                        break
                    continue
                collected.append(value)
            if collected:
                aggregated.extend(collected)
                col_max = max(collected)
                size = len(collected)
                if (
                    not best
                    or (size >= 3 > best_len)
                    or (size >= 3 and best_len >= 3 and (best_max is None or col_max > best_max))
                    or (best_len < 3 and size < 3 and (best_max is None or col_max > best_max))
                ):
                    best = collected
                    best_len = size
                    best_max = col_max
        return best, aggregated

    total_block, total_values = numbers_after_marker('כ"הס', limit=16)
    block_alt, values_alt = numbers_after_marker('סה"כ', limit=16)
    if block_alt and (not total_block or max(block_alt) > max(total_block)):
        total_block = block_alt
    total_values.extend(values_alt)

    total = find_amount_before_marker(lines, 'םלוש כ"הס', prefer_inline=True)
    if total is None:
        total = find_amount_before_marker(lines, 'םולשתל כ"הס', prefer_inline=True)
    if total is None:
        total = find_amount_before_marker(lines, "םולשתל", prefer_inline=True)
    base_before_vat = find_amount_before_marker(lines, 'מ"עמ ינפל', prefer_inline=True)
    base_candidates = numeric_values_near_marker(lines, 'מ"עמ ינפל')
    vat = find_amount_before_marker(lines, 'לע מ"עמ')
    if vat is None:
        vat = find_amount_before_marker(lines, 'מ"עמ ')
    vat_candidates = numeric_values_near_marker(lines, 'לע מ"עמ')
    explicit_vat_rate = extract_vat_rate_from_text(text)
    dbg(
        f"initial total={total}, base_before_vat={base_before_vat}, "
        f"base_candidates={base_candidates}, vat_initial={vat}, "
        f"vat_candidates={vat_candidates}, explicit_vat_rate={explicit_vat_rate}"
    )

    if total is None:
        for marker in ('סה"כ', "סה״כ", "סהכ", 'סה"כ לתשלום', 'סה"כ לתשלום בש"ח'):
            total = find_amount_before_marker(lines, marker)
            if total is not None:
                break
    if total is None:
        match = re.search(r"סה.?\"?כ.?[:\-]?\s*([\d.,]+)", text)
        if match:
            total = parse_number(match.group(1))
    if total is None:
        patterns = [
            r"סה.?\"?כ.? ?לתשלום[^\d]*([\d.,]+)",
            r"([\d.,]+)\s+סה.?\"?כ.? ?לתשלום",
            r"סה.?\"?כ.? ?לתשלום(?:.|\n){0,40}?([\d.,]+)",
            r"כ.?\"?הס[^\n]{0,40}?םולשתל[^\n]{0,40}?ח.?\"?ש[^\n]{0,40}?מ\"?עמ[^\d]*([\d.,]+)",
            r"([\d.,]+)\s+מ\"?עמ[^\n]{0,40}?ח.?\"?ש[^\n]{0,40}?םולשתל[^\n]{0,40}?כ.?\"?הס",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
            if match:
                total = parse_number(match.group(1))
                if total is not None:
                    break
    if total is None:
        total = amount_near_markers(
            text,
            [
                r"סה.?\"?כ.? ?לתשלום",
                r"כ.?\"?הס[^\n]{0,40}?םולשתל[^\n]{0,40}?מ\"?עמ",
                r"ח.?\"?ש[^\n]{0,20}?םולשתל",
            ],
            prefer="max",
        )
    if total is None:
        match = re.search(
            r"סה.?\"?כ.? ?יגבה[^:]*:\s*([0-9,\.\s]+?)(?:\n|$)",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            token = re.sub(r"\s+", "", match.group(1))
            total = parse_number(token)
    if total is None or (total is not None and total <= 5):
        match = re.search(
            r"סה.{0,4}?יגבה[^:]*:\s*((?:.|\n)*?)\n\s*4",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            block = match.group(1)
            token = re.sub(r"[^0-9.,]", "", block)
            total = parse_number(token)
            if (total is None or total < 50 or "\n" in block) and token:
                reversed_token = token[::-1]
                alt = parse_number(reversed_token)
                if alt is not None:
                    total = alt
    if total is None:
        match = re.search(r"סה.?\"?כ.? ?יגבה[^0-9]+([\d.,]+)", text)
        if match:
            total = parse_number(match.group(1))
    if total_block:
        block_max = max(total_block)
        if block_max and block_max > 0:
            total = block_max
    if total is None:
        matches = re.findall(r"₪\s*([\d.,]+)\s*[:\-]?\s*כ[\"״']?הס", text)
        amounts = [parse_number(token) for token in matches]
        numeric = [val for val in amounts if val is not None]
        if numeric:
            total = max(numeric)
    currency_tokens = re.findall(r"₪\s*([\d.,]+)", text)
    if total is None:
        total = select_amount(currency_tokens[::-1])
    if total is not None and total <= 5:
        fallback_total = select_amount(currency_tokens[::-1])
        if fallback_total and fallback_total > total:
            total = fallback_total
    if base_candidates:
        candidates = base_candidates[:]
        if total is not None:
            below_total = [val for val in candidates if val < total]
            if below_total:
                candidates = below_total
        if candidates:
            base_before_vat = max(candidates)
    dbg(f"total after heuristics={total}, base_before_vat={base_before_vat}")

    if base_before_vat is None and total is not None and total_values:
        approx_base = total / 1.18 if total > 0 else None
        if approx_base:
            candidates = [val for val in total_values if 0 < val < total]
            if candidates:
                base_before_vat = min(candidates, key=lambda val: abs(val - approx_base))

    if vat is None:
        vat_patterns = [
            r"סה.?\"?כ.? ?מע\"?מ[^\d]*([\d.,]+)",
            r"([\d.,]+)\s+סה.?\"?כ.? ?מע\"?מ",
            r"מ\"?עמ[^\n]{0,30}?כ.?\"?הס[^\d]*([\d.,]+)",
            r"([\d.,]+)\s+כ.?\"?הס[^\n]{0,30}?מ\"?עמ",
        ]
        for pattern in vat_patterns:
            match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
            if match:
                vat = parse_number(match.group(1))
                if vat is not None:
                    break
    if vat is None:
        vat = amount_near_markers(
            text,
            [
                r"סה.?\"?כ.? ?מע\"?מ",
                r"מ\"?עמ[^\n]{0,30}?כ.?\"?הס",
            ],
            prefer="min",
        )
    if vat is None:
        for line in lines:
            if 'מ"עמ' in line:
                if 'מ"עמל' in line and "₪" not in line and "%" not in line:
                    continue
                tokens = re.findall(r"[\d.,]+", line)
                amount = select_amount(tokens[::-1])
                if amount is not None:
                    vat = amount
                    break
            if vat is not None:
                break

    if total is not None and vat_candidates:
        filtered_vat = sorted(val for val in vat_candidates if 0 < val < total)
        replacement_vat = None
        for candidate in filtered_vat:
            rate_candidate = vat_rate_estimate(total, candidate)
            if rate_candidate is None or abs(rate_candidate - 18.0) < 1.0:
                replacement_vat = candidate
                break
        if replacement_vat is None and filtered_vat:
            replacement_vat = filtered_vat[0]
        if replacement_vat is not None:
            vat = replacement_vat

    if vat is None and total is not None and base_before_vat is not None:
        candidate_vat = round(total - base_before_vat, 2)
        if candidate_vat >= 0:
            vat = candidate_vat

    if vat is not None and total is not None and vat > total:
        vat = None
    if vat is None:
        vat = amount_near_markers(
            text,
            [
                r"סה.?\"?כ.? ?מע\"?מ",
                r"מ\"?עמ[^\n]{0,30}?כ.?\"?הס",
            ],
            prefer="min",
        )

    if (
        vat is None
        and total is not None
        and base_before_vat is not None
        and base_before_vat < total
    ):
        vat_candidate = round(total - base_before_vat, 2)
        if vat_candidate >= 0:
            vat = vat_candidate

    currency_amounts: List[float] = []
    if total is not None or vat is not None:
        for token in currency_tokens:
            amount = parse_number(token)
            if amount is not None:
                currency_amounts.append(amount)
    dbg(f"currency_amounts={currency_amounts}")

    if vat is None and total is not None:
        smaller = [amt for amt in currency_amounts if amt < total]
        if smaller:
            vat_candidate = round(total - max(smaller), 2)
            if vat_candidate >= 0:
                vat = vat_candidate
    elif vat is not None and total is not None:
        smaller = [amt for amt in currency_amounts if amt < total]
        if smaller:
            vat_candidate = round(total - max(smaller), 2)
            if 0 < vat_candidate < vat:
                vat = vat_candidate

    rate = vat_rate_estimate(total, vat)
    dbg(f"vat after heuristics={vat}, vat_rate={rate}")
    if (
        rate is not None
        and total is not None
        and base_before_vat is not None
        and base_before_vat < total
        and abs(rate - 18.0) > 1.0
    ):
        recalculated_vat = round(total - base_before_vat, 2)
        if recalculated_vat >= 0:
            vat = recalculated_vat
            dbg(f"vat replaced via base diff → {vat}")

    municipal_markers = [
        "ארנונה",
        "עיריית",
        "רשות מקומית",
        "תאגיד מים",
        "onecity",
    ]
    is_municipal = any(marker in text for marker in municipal_markers)
    if not is_municipal:
        if (("פתח תק" in text) or ("הווקת חתפ" in text)) and ("חוב" in text):
            is_municipal = True
    block_source = pdfminer_lines or lines
    block_sum, breakdown_values = sum_numeric_block(
        block_source,
        ['ח"שב', "חשב כ"],
        ["סכנה", "סה", 'סה"', "סה''כ יגבה", 'סה"כ יגבה', 'סה"כ יגבה'],
    )
    if is_municipal:
        if block_sum is not None:
            if total is None or total < 50 or abs(total - block_sum) > 1.0:
                total = block_sum
                dbg(f"municipal total derived from block sum={total}")
        vat = 0.0
        dbg("municipal invoice detected → forcing VAT=0")

    return {
        "invoice_total": total,
        "invoice_vat": vat,
        "vat_rate": explicit_vat_rate
        if explicit_vat_rate is not None
        else vat_rate_estimate(total, vat),
        "municipal": is_municipal,
        "breakdown_sum": block_sum,
        "breakdown_values": breakdown_values,
        "base_before_vat": base_before_vat,
    }


def parse_invoice(path: Path, debug: bool = False) -> InvoiceRecord:
    try:
        text_pdfminer = extract_text(path)
    except Exception:  # pragma: no cover - defensive
        text_pdfminer = ""

    if not text_pdfminer:
        return InvoiceRecord(
            source_file=path.name,
            notes="extract_text_failed",
        )

    text = text_pdfminer
    used_fallback = False
    fallback_text = ""
    if needs_fallback_text(text_pdfminer):
        fallback_text = extract_text_with_pymupdf(path)
        if fallback_text:
            text = fallback_text
            used_fallback = True

    if fallback_text:
        pymupdf_text_cache: Optional[str] = fallback_text
        pymupdf_lines_cache: Optional[List[str]] = extract_lines(fallback_text)
    else:
        pymupdf_text_cache = None
        pymupdf_lines_cache = None

    def ensure_pymupdf_data() -> None:
        nonlocal pymupdf_text_cache, pymupdf_lines_cache
        if pymupdf_text_cache is not None:
            return
        if not HAVE_PYMUPDF:
            pymupdf_text_cache = ""
            pymupdf_lines_cache = []
            return
        extra = extract_text_with_pymupdf(path)
        pymupdf_text_cache = extra or ""
        pymupdf_lines_cache = extract_lines(pymupdf_text_cache) if pymupdf_text_cache else []

    def get_pymupdf_text() -> str:
        ensure_pymupdf_data()
        return pymupdf_text_cache or ""

    def get_pymupdf_lines() -> List[str]:
        ensure_pymupdf_data()
        return pymupdf_lines_cache or []

    lines = extract_lines(text)
    if debug:
        print(f"\n[debug][{path.name}] === pdfminer text preview ===")
        preview_pdfminer = "\n".join(text_pdfminer.replace("\r", "\n").splitlines()[:40])
        print(preview_pdfminer or "(no text extracted)")
        if fallback_text:
            print(f"\n[debug][{path.name}] === PyMuPDF text preview ===")
            preview_pymupdf = "\n".join(fallback_text.replace("\r", "\n").splitlines()[:40])
            print(preview_pymupdf or "(no fallback text)")
        print(f"\n[debug][{path.name}] === normalized lines preview ===")
        preview = "\n".join(lines[:40])
        print(preview or "(no text extracted)")

    record = InvoiceRecord(source_file=path.name)
    record.invoice_id = infer_invoice_id(lines, text)
    record.invoice_date = infer_invoice_date(text)
    invoice_from = infer_invoice_from(lines, text)
    if not invoice_from or invoice_from.startswith(":"):
        extra_text = get_pymupdf_text()
        extra_lines = get_pymupdf_lines()
        if extra_text and extra_lines:
            alt_from = infer_invoice_from(extra_lines, extra_text)
            if alt_from:
                invoice_from = alt_from
    if invoice_from and len(invoice_from) > 120:
        invoice_from = invoice_from[:117] + "..."
    record.invoice_from = invoice_from
    invoice_for = infer_invoice_for(lines, text)
    if not invoice_for:
        extra_text = get_pymupdf_text()
        extra_lines = get_pymupdf_lines()
        if extra_text and extra_lines:
            invoice_for = infer_invoice_for(extra_lines, extra_text)
    record.invoice_for = invoice_for
    lines_pdfminer = extract_lines(text_pdfminer)
    totals = infer_totals(
        lines,
        text,
        debug=debug,
        label=path.name,
        pdfminer_lines=lines_pdfminer,
    )
    record.invoice_total = totals.get("invoice_total")
    record.invoice_vat = totals.get("invoice_vat")
    record.breakdown_sum = totals.get("breakdown_sum")
    if totals.get("breakdown_values"):
        record.breakdown_values = totals["breakdown_values"]
    record.base_before_vat = totals.get("base_before_vat")
    record.vat_rate = totals.get("vat_rate")
    record.municipal = totals.get("municipal")
    if (
        record.breakdown_sum is not None
        and record.invoice_total is not None
        and abs(record.breakdown_sum - record.invoice_total) > 1.0
    ):
        if record.notes:
            record.notes += "; "
        else:
            record.notes = ""
        record.notes += "Total differs from breakdown sum"
    if totals.get("municipal"):
        if not record.invoice_from:
            if "פתח תק" in text or "הווקת חתפ" in text:
                record.invoice_from = "עיריית פתח תקווה"
            else:
                record.invoice_from = "רשות מקומית"
        if record.invoice_vat is None:
            record.invoice_vat = 0.0
    period_start, period_end, period_label = extract_period_info(text)
    record.period_start = period_start
    record.period_end = period_end
    record.period_label = period_label
    record.due_date = extract_due_date(text)
    references = extract_reference_numbers(text)
    if references:
        record.reference_numbers = references
    category, category_confidence, category_rule = classify_invoice(
        text, record.invoice_from, bool(record.municipal)
    )
    record.category = category
    record.category_confidence = category_confidence
    record.category_rule = category_rule
    record.data_source = "pymupdf" if used_fallback else "pdfminer"
    record.duplicate_hash = file_sha256(path)
    record.parse_confidence = compute_parse_confidence(record)
    if debug:
        if used_fallback:
            print(f"[debug][{path.name}] used PyMuPDF fallback for text extraction")
        print(
            f"[debug][{path.name}] summary: total={record.invoice_total} "
            f"vat={record.invoice_vat} id={record.invoice_id} from={record.invoice_from}"
        )
    return record


def generate_report(
    input_dir: Path,
    *,
    selected_files: Optional[List[str]] = None,
    debug: bool = False,
) -> List[InvoiceRecord]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    records: List[InvoiceRecord] = []
    candidates: List[Path]
    if selected_files:
        candidates = []
        for name in selected_files:
            candidate = Path(name)
            if not candidate.is_absolute():
                candidate = input_dir / candidate
            candidates.append(candidate)
    else:
        candidates = sorted(input_dir.glob("*.pdf"))

    for path in candidates:
        if not path.exists():
            if debug:
                print(f"[debug] Skip missing file: {path}")
            continue
        records.append(parse_invoice(path, debug=debug))
    return records


def write_json(records: List[InvoiceRecord], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump([asdict(rec) for rec in records], fh, ensure_ascii=False, indent=2)


def write_csv(records: List[InvoiceRecord], output_path: Path) -> None:
    fields = [
        "source_file",
        "invoice_id",
        "invoice_date",
        "invoice_from",
        "invoice_for",
        "invoice_total",
        "invoice_vat",
        "currency",
        "breakdown_sum",
        "breakdown_values",
        "notes",
        "base_before_vat",
        "vat_rate",
        "period_start",
        "period_end",
        "period_label",
        "due_date",
        "category",
        "category_confidence",
        "category_rule",
        "reference_numbers",
        "data_source",
        "parse_confidence",
        "municipal",
        "duplicate_hash",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(fields)
        for record in records:
            writer.writerow(record.to_csv_row(fields))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a report from downloaded invoice PDFs.")
    parser.add_argument(
        "--input-dir",
        default="invoices_outlook",
        help="Directory containing invoice PDF files (default: invoices_outlook)",
    )
    parser.add_argument(
        "--json-output",
        default="invoice_report.json",
        help="Path for JSON report (default: invoice_report.json)",
    )
    parser.add_argument(
        "--csv-output",
        default="invoice_report.csv",
        help="Path for CSV report (default: invoice_report.csv)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print detailed parsing diagnostics per invoice.",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=None,
        help="Specific invoice file names to process (relative to input dir).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_pdfminer_logging(args.debug)
    input_dir = Path(args.input_dir)
    selected = args.files if args.files else None
    records = generate_report(input_dir, selected_files=selected, debug=args.debug)
    write_json(records, Path(args.json_output))
    write_csv(records, Path(args.csv_output))
    print(
        f"Generated {len(records)} records → {args.json_output}, {args.csv_output}",
    )


if __name__ == "__main__":  # pragma: no cover
    main()
