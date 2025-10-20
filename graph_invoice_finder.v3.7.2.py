#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Graph Invoice Finder (v3.7.2)

שינויים עיקריים לעומת v3.7.1:
- תיקון הורדת צרופות: אין שימוש ב-@odata.type בתוך $select; תוכן fileAttachment נמשכת דרך /$value.
- אימות חשבונית גמיש: --verify none|light|strict (+ --verify-threshold לעקיפה ידנית).
- ריכוך בלינקים: --accept-octet-stream מאפשר להוריד PDF גם כש-Content-Type הוא octet-stream מדומיינים מותרים.
"""

import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import msal
import pandas as pd
import requests

# --- HTML parsing (אופציונלי) ---
try:
    from bs4 import BeautifulSoup  # type: ignore

    HAS_BS4 = True
except Exception:
    HAS_BS4 = False

# --- PDF engines ---
try:
    import fitz  # PyMuPDF

    HAS_PYMUPDF = True
except Exception:
    HAS_PYMUPDF = False

try:
    from PyPDF2 import PdfReader  # fallback only

    HAS_PYPDF = True
except Exception:
    HAS_PYPDF = False

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.Read"]

DEBUG = False
PDF_ENGINE = "auto"  # יעודכן אחרי argparse

# =========================
# תצורה
# =========================

DEFAULTS = {
    "select_fields": "id,subject,from,receivedDateTime,hasAttachments,body,bodyPreview,webLink",
    "page_size_search": 50,
    "max_pages": 20,
    "lookback_days": 120,
    "min_confidence": 0.55,
    "timeout_sec": 30,
    "http_timeout": 25,
    "min_pdf_size_bytes": 6_000,
}

# אימות PDF: ספים ברירת מחדל לפי מצב
VERIFY_DEFAULTS = {
    "none": 0.0,  # לא מאמת – שומר כל PDF
    "light": 0.30,  # סף נמוך
    "strict": 0.45,  # סף קודם (ברירת המחדל)
}

DEFAULT_SENDER_BOOST = ["+@bezeq.co.il"]

KEYWORDS = {
    "hebrew_core": [
        "חשבונית",
        "חשבונית מס",
        "קבלה",
        "אסמכתא",
        "תשלום",
        "דרישת תשלום",
        "קבלה מס",
        "חשבונית מס קבלה",
        "חיוב",
        "זיכוי",
        "שובר תשלום",
    ],
    "english_core": [
        "invoice",
        "tax invoice",
        "receipt",
        "payment receipt",
        "billing statement",
        "payment request",
        "charge",
        "credit note",
    ],
    "hebrew_context": [
        "מספר חשבונית",
        "סכום לתשלום",
        "יתרה לתשלום",
        "פירוט חיובים",
        "לצפייה בחשבונית",
        "הורדה",
        "הורד קובץ",
        "קישור לחשבונית",
    ],
    "english_context": [
        "invoice number",
        "amount due",
        "balance due",
        "view invoice",
        "download invoice",
        "download receipt",
        "statement",
    ],
    "municipal_he": [
        "ארנונה",
        "שובר תשלום",
        "עיריית",
        "עיריה",
        "עירייה",
        "רשות מקומית",
        "תאגיד מים",
        "ביוב",
        "אגרת",
        "היטל",
    ],
    "donation_he": ["תרומה", "עמותה", 'מלכ"ר', 'ע"ר'],
}

ATTACHMENT_PREF = {
    "extensions": [".pdf", ".tif", ".tiff", ".jpg", ".jpeg", ".png", ".xlsx", ".xls"],
    "name_hints": ["invoice", "receipt", "חשבונית", "קבלה", "שובר", "ארנונה"],
}

ATTACHMENT_NEG_HINTS = [
    "הודעה",
    "מידע",
    "דף הסבר",
    "הסבר",
    "עלון",
    "פרסום",
    "עדכון",
    "notice",
    "info",
    "information",
    "explainer",
    "newsletter",
    "promo",
    "marketing",
]

LINK_RULES = {
    "require_https": True,
    "url_keywords": [
        "invoice",
        "receipt",
        "statement",
        "bill",
        "חשבונית",
        "קבלה",
        "תשלום",
        "payment",
        "download",
        "voucher",
        "shovar",
        "ארנונה",
    ],
    "trusted_providers": [
        "greeninvoice.co.il",
        "icount.co.il",
        "ezcount.co.il",
        "priority-software.com",
        "sap.com",
        "zoho.com",
        "xero.com",
        "quickbooks.intuit.com",
        "stripe.com",
        "paypal.com",
        "wix.com",
        "shopify.com",
        "tax.gov.il",
        "freshbooks.com",
        "waveapps.com",
        "bezeq.co.il",
        "cardcom.co.il",
    ],
    "heuristics": {
        "path_patterns": [
            "invoice",
            "receipt",
            "billing",
            "payments",
            "download",
            "documents",
            "חשבונית",
            "קבלה",
            "תשלום",
            "voucher",
            "ארנונה",
        ],
        "file_like_suffixes": [".pdf"],
    },
    "allowed_http_providers": ["citypay.co.il"],
    "tracking_domains": [
        "webversion.net",
        "web-view.net",
        "mandrillapp.com",
        "s4.exct.net",
    ],
    "tracking_subdomain_prefixes": ["click.", "image.", "view.", "trailer."],
}

LANG_WEIGHTS = {"he": 1.2, "en": 1.0}

# ===== אסטרטגיות (AQS בלבד) =====
STRATEGIES = [
    {
        "name": "attachments_and_keywords_recent",
        "description": "מילות מפתח רחבות (חשבונית/קבלה/Invoice) לקלוט נושאים/גופים קלאסיים; צרופות מטופלות בצד לקוח.",
        "search": "invoice OR receipt OR חשבונית OR קבלה",
    },
    {
        "name": "keywords_only_recent",
        "description": "רשת רחבה יותר כולל statement/billing/תשלום — מועיל לחשבוניות-לינק שמתחמקות ממילה 'חשבונית'.",
        "search": "(invoice OR receipt OR statement OR billing OR חשבונית OR קבלה OR תשלום)",
    },
    {
        "name": "hebrew_bias",
        "description": "הטיה לעברית — ביטויים שכיחים כמו 'חשבונית מס' ו'חשבונית מס קבלה'.",
        "search": '(חשבונית OR "חשבונית מס" OR קבלה OR תשלום OR "חשבונית מס קבלה")',
    },
    {
        "name": "provider_whitelist_bump",
        "description": "כיוון לספקים מוכרים (GreenInvoice, iCount, QuickBooks, Stripe, tax.gov.il, Cardcom).",
        "search": '("greeninvoice.co.il" OR "icount.co.il" OR "ezcount.co.il" OR "quickbooks.intuit.com" OR "stripe.com" OR "paypal.com" OR "zoho.com" OR "xero.com" OR "shopify.com" OR "tax.gov.il" OR "cardcom.co.il")',
    },
    {
        "name": "municipal_hebrew",
        "description": "מיקוד בפריטי ארנונה/עיריות/שוברי תשלום בעברית.",
        "search": '(ארנונה OR "שובר תשלום" OR עיריית OR עיריה OR "רשות מקומית" OR "תאגיד מים" OR אגרת OR היטל)',
    },
]

# =========================
# עזר
# =========================


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_any_dt(s: str) -> dt.datetime:
    s = (s or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        d = dt.datetime.strptime(s, "%Y-%m-%d")
        return d.replace(tzinfo=dt.timezone.utc)
    s2 = s.replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(s2)
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


URL_RE = re.compile(r'https?://[^\s<>"\'\]]+|http://[^\s<>"\'\]]+', re.IGNORECASE)


def extract_urls_from_body(body: Dict) -> List[str]:
    content = (body or {}).get("content", "") or ""
    txt = unescape(content)
    urls = URL_RE.findall(txt)
    urls = list(dict.fromkeys([u.strip(").,]}>\"'") for u in urls]))
    return urls


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc
        host = re.sub(r"^www\.", "", host).lower()
        return host
    except Exception:
        return ""


def path_of(url: str) -> str:
    try:
        return urlparse(url).path or "/"
    except Exception:
        return "/"


def email_addr_of_from(frm: Dict) -> Tuple[str, str]:
    try:
        ea = (frm or {}).get("emailAddress", {})
        name = ea.get("name") or ""
        email = (ea.get("address") or "").lower()
        return name, email
    except Exception:
        return "", ""


def sender_domain(email: str) -> str:
    try:
        return email.split("@", 1)[1].lower()
    except Exception:
        return ""


def is_trusted_domain(dom: str, trusted_list: List[str]) -> bool:
    dom = (dom or "").lower()
    for root in trusted_list:
        root = root.lower()
        if dom == root or dom.endswith("." + root):
            return True
    return False


def is_http_allowed(dom: str, allowed_http_list: List[str]) -> bool:
    dom = (dom or "").lower()
    for root in allowed_http_list:
        root = root.lower()
        if dom == root or dom.endswith("." + root):
            return True
    return False


def is_tracking_domain(dom: str) -> bool:
    if dom in LINK_RULES["tracking_domains"]:
        return True
    for pref in LINK_RULES["tracking_subdomain_prefixes"]:
        if dom.startswith(pref):
            return True
    return False


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-. ()\u0590-\u05FF]", "_", name)[:200]


def score_links(
    urls: List[str], trusted_providers: List[str], allowed_http_providers: List[str]
) -> Tuple[List[str], float]:
    path_patterns = [p.lower() for p in LINK_RULES["heuristics"]["path_patterns"]]
    keywords = [k.lower() for k in LINK_RULES["url_keywords"]]
    suffixes = [s.lower() for s in LINK_RULES["heuristics"]["file_like_suffixes"]]
    kept, any_trust, any_kw_or_pat, any_suf = [], False, False, False
    for u in urls:
        u_low = u.lower()
        is_https = u_low.startswith("https://")
        dom = domain_of(u)
        if not is_https:
            if not (
                u_low.startswith("http://")
                and is_http_allowed(dom, allowed_http_providers)
            ):
                continue
        dom_trust = is_trusted_domain(dom, trusted_providers)
        tracky = is_tracking_domain(dom)
        path = path_of(u).lower()
        has_kw = any(k in u_low for k in keywords)
        has_pat = any(p in path for p in path_patterns)
        has_suf = any(u_low.endswith(s) or (("?" + s) in u_low) for s in suffixes)
        if tracky and not (has_kw or has_pat or has_suf or dom_trust):
            continue
        if dom_trust or has_kw or has_pat or has_suf:
            kept.append(u)
            any_trust |= dom_trust
            any_kw_or_pat |= has_kw or has_pat
            any_suf |= has_suf
    score = 0.0
    if any_trust:
        score += 0.4
    if any_suf:
        score += 0.25
    if any_kw_or_pat:
        score += 0.15
    return kept, min(score, 0.7)


def body_as_text(body: Dict) -> str:
    if not body:
        return ""
    ct = (body.get("contentType") or "").lower()
    c = body.get("content") or ""
    if ct == "html":
        c = re.sub(r"<script.*?>.*?</script>", " ", c, flags=re.I | re.S)
        c = re.sub(r"<style.*?>.*?</style>", " ", c, flags=re.I | re.S)
        c = re.sub(r"<[^>]+>", " ", c)
    return unescape(c)


def count_hits(text: str, needles: List[str]) -> int:
    t = text.lower()
    return sum(1 for n in needles if n.lower() in t)


def language_confidence(
    subject: str, preview: str, body_text: str
) -> Tuple[float, Dict[str, int]]:
    he_core = KEYWORDS["hebrew_core"] + KEYWORDS["hebrew_context"]
    en_core = KEYWORDS["english_core"] + KEYWORDS["english_context"]
    blob = f"{subject}\n{preview}\n{body_text}".lower()
    hits_he = count_hits(blob, he_core)
    hits_en = count_hits(blob, en_core)
    score = hits_he * 1.2 * 0.05 + hits_en * 1.0 * 0.05
    return min(score, 0.8), {"hits_he": hits_he, "hits_en": hits_en}


def prefers_attachment(name: str, content_type: str) -> bool:
    n = (name or "").lower()
    ct = (content_type or "").lower()
    if any(n.endswith(ext) for ext in ATTACHMENT_PREF["extensions"]):
        return True
    if any(h in n for h in ATTACHMENT_PREF["name_hints"]):
        return True
    if "pdf" in ct:
        return True
    return False


SUBJECT_STRONG_RE = re.compile(r"\b(חשבונית|קבלה|invoice|receipt)\b", re.I)
DONATION_HE_TOKENS = [t.lower() for t in KEYWORDS["donation_he"]]
ATT_NOTICE_RE = re.compile(
    r"(הודעה|מידע|דף\s*הסבר|הסבר|notice|info|information).{0,20}(חשבונית|קבלה)", re.I
)


def subject_strong_bonus(subj: str) -> float:
    s = (subj or "").lower()
    if re.search(r"(חשבונית|קבלה)", s) or re.search(r"\b(invoice|receipt)\b", s):
        return 0.35
    return 0.0


def donation_bonus(subj: str) -> float:
    s = (subj or "").lower()
    if "קבלה" in s and any(t in s for t in DONATION_HE_TOKENS):
        return 0.2
    return 0.0


def attachment_notice_penalty(attachments: List[Dict]) -> float:
    for a in attachments or []:
        name = a.get("name") or ""
        if ATT_NOTICE_RE.search(name):
            return -0.25
    return 0.0


def municipal_attachment_bonus(
    subject: str, attachments: List[Dict]
) -> Tuple[float, Dict[str, Any]]:
    subj = (subject or "").lower()
    muni_hits = count_hits(subj, KEYWORDS["municipal_he"])
    bonus = 0.0
    matched_files = []
    if muni_hits > 0 and attachments:
        for a in attachments:
            name = (a.get("name") or "").lower()
            ct = (a.get("contentType") or "").lower()
            if ct == "application/pdf" and re.match(r"^\d{6,}\.pdf$", name):
                matched_files.append(name)
        if matched_files:
            bonus = 0.18
    return bonus, {"muni_hits": muni_hits, "files": matched_files}


def explain_links(urls, kept, link_score) -> Dict[str, Any]:
    return {"candidates": urls, "kept": kept, "score": link_score}


def explain_language(
    subject, preview, body_text, lang_score, lang_hits
) -> Dict[str, Any]:
    return {
        "subject": subject,
        "preview": preview,
        "he_hits": lang_hits.get("hits_he", 0),
        "en_hits": lang_hits.get("hits_en", 0),
        "score": lang_score,
    }


def explain_attachments(hits) -> Dict[str, Any]:
    return {"kept": hits, "count": len(hits)}


# =========================
# Graph Client
# =========================


@dataclass
class GraphClient:
    client_id: str
    authority: str
    _session: requests.Session = field(init=False, default_factory=requests.Session)
    _token: Optional[str] = field(init=False, default=None)

    def login(self):
        app = msal.PublicClientApplication(self.client_id, authority=self.authority)
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(
                "Device flow creation failed. Check client id / authority."
            )
        print("== Device Code Authentication ==")
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            raise RuntimeError(f"Auth failed: {result}")
        self._token = result["access_token"]

    @property
    def headers_auth(self):
        if not self._token:
            raise RuntimeError("Not authenticated")
        return {"Authorization": f"Bearer {self._token}"}

    def get(self, url: str, params: Dict, use_search: bool = False) -> Dict:
        headers = dict(self.headers_auth)
        if use_search:
            headers["ConsistencyLevel"] = "eventual"
        if DEBUG:
            print(f"[GET] {url} params={params} use_search={use_search}")
        r = self._session.get(
            url, headers=headers, params=params, timeout=DEFAULTS["timeout_sec"]
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Graph GET failed {r.status_code}: {r.text}")
        return r.json()


# =========================
# Core Search / Fetch
# =========================


def run_strategy(
    gc: GraphClient, strategy: Dict, page_size: int, max_pages: int, select_fields: str
) -> List[Dict]:
    url = f"{GRAPH_BASE}/me/messages"
    params = {
        "$select": select_fields,
        "$top": str(page_size),
        "$search": strategy["search"],
    }
    out, pages = [], 0
    next_url, next_params = url, params
    while next_url and pages < max_pages:
        pages += 1
        data = gc.get(next_url, next_params, use_search=True)
        out.extend(data.get("value", []))
        next_url = data.get("@odata.nextLink")
        next_params = {}
    for m in out:
        m["_matched_strategy"] = strategy["name"]
        m["_matched_strategy_description"] = strategy["description"]
    return out


# =========================
# בדיקות קלט (תאריכים)
# =========================


def parse_user_date_safe(label: str, s: Optional[str]) -> Optional[dt.datetime]:
    if not s:
        return None
    try:
        return parse_any_dt(s)
    except Exception:
        msg = (
            f"⚠️ ערך לא תקין עבור {label}: {s}\n"
            "פורמטים נתמכים:\n"
            "  • YYYY-MM-DD (למשל: 2025-09-01)\n"
            "  • ISO8601 (למשל: 2025-09-01T00:00:00Z או 2025-09-01T03:00:00+03:00)\n"
        )
        raise SystemExit(msg)


def validate_date_window(
    start_dt: Optional[dt.datetime], end_dt: Optional[dt.datetime]
):
    if start_dt and end_dt and end_dt <= start_dt:
        msg = (
            "⚠️ טווח תאריכים לא תקין: --end-date חייב להיות מאוחר מ- --start-date.\n"
            f"start: {start_dt.isoformat()}  end: {end_dt.isoformat()}\n"
            "דוגמה תקינה: --start-date 2025-07-01 --end-date 2025-09-30\n"
        )
        raise SystemExit(msg)


# =========================
# הורדת צרופות — תיקון v3.7.2
# =========================


def _get_attachment_bytes(
    gc: GraphClient, message_id: str, attachment_id: str
) -> bytes:
    url = f"{GRAPH_BASE}/me/messages/{message_id}/attachments/{attachment_id}/$value"
    headers = dict(gc.headers_auth)
    headers["Accept"] = "*/*"
    r = gc._session.get(url, headers=headers, timeout=DEFAULTS["timeout_sec"])
    if r.status_code >= 400:
        raise RuntimeError(f"Graph GET failed {r.status_code}: {r.text}")
    return r.content


def fetch_attachments(
    gc: GraphClient, message_id: str, want_content: bool = False
) -> List[Dict]:
    base = f"{GRAPH_BASE}/me/messages/{message_id}/attachments"
    url = base
    attachments: List[Dict] = []
    while url:
        params = {"$select": "id,name,contentType,size"}  # אסור לבחור @odata.type
        data = gc.get(url, params=params, use_search=False)
        for a in data.get("value", []):
            att = {
                "id": a.get("id"),
                "name": a.get("name"),
                "contentType": a.get("contentType"),
                "size": a.get("size"),
                "odata_type": a.get("@odata.type", ""),
                "contentBytes": None,
            }
            if want_content:
                try:
                    raw = _get_attachment_bytes(gc, message_id, att["id"])
                    att["contentBytes"] = base64.b64encode(raw).decode("ascii")
                except Exception as e:
                    att["contentBytes"] = None
                    att["error"] = f"content_fetch_failed:{e}"
            attachments.append(att)
        url = data.get("@odata.nextLink")
    return attachments


# =========================
# ניקוד + בניית שורה
# =========================


def normalize_from(frm: Dict) -> str:
    name, email = email_addr_of_from(frm or {})
    return f"{name} <{email}>" if email else name


def build_row(
    msg: Dict,
    kept_links: List[str],
    attach_hits: List[Dict],
    lang_score: float,
    link_score: float,
    lang_hits: Dict[str, int],
    *,
    include_explain: bool = False,
    body_text_for_explain: str = "",
) -> Dict:
    subject = msg.get("subject") or ""
    preview = msg.get("bodyPreview") or ""
    frm = normalize_from(msg.get("from") or {})
    rid = msg.get("id")
    rdt = msg.get("receivedDateTime")
    web = msg.get("webLink")
    strategy = msg.get("_matched_strategy", "")
    strategy_desc = msg.get("_matched_strategy_description", "")
    confidence = min(1.0, lang_score + link_score + (0.25 if attach_hits else 0.0))
    row = {
        "id": rid,
        "subject": subject,
        "from": frm,
        "receivedDateTime": rdt,
        "hasAttachments": bool(msg.get("hasAttachments")),
        "matched_strategy": strategy,
        "matched_strategy_description": strategy_desc,
        "match_confidence": round(confidence, 3),
        "lang_hits_he": lang_hits.get("hits_he", 0),
        "lang_hits_en": lang_hits.get("hits_en", 0),
        "matched_links": kept_links,
        "matched_attachments": [
            {k: v for k, v in a.items() if k != "contentBytes"} for a in attach_hits
        ],
        "webLink": web,
    }
    if include_explain:
        row["explanations"] = {
            "language": explain_language(
                subject, preview, body_text_for_explain, lang_score, lang_hits
            ),
            "links": explain_links(
                extract_urls_from_body(msg.get("body") or {}), kept_links, link_score
            ),
            "attachments": explain_attachments(attach_hits),
        }
    return row


def apply_sender_boost(base_conf: float, frm: Dict, rules: List[str]) -> float:
    if not rules:
        return base_conf
    _, email = email_addr_of_from(frm or {})
    dom = sender_domain(email)
    delta = 0.0
    for rule in rules:
        rule = rule.strip()
        if not rule:
            continue
        sign = +1.0 if rule.startswith("+") else -1.0
        token = rule[1:].lower()
        if token.startswith("@") and dom == token[1:]:
            delta += 0.2 * sign
        elif token == email:
            delta += 0.25 * sign
    return min(1.0, max(0.0, base_conf + delta))


def apply_negative_keywords(
    base_conf: float, subject: str, preview: str, body_text: str, negatives: List[str]
) -> Tuple[float, int]:
    if not negatives:
        return base_conf, 0
    blob = f"{subject}\n{preview}\n{body_text}".lower()
    hits = sum(1 for w in negatives if w.strip() and w.lower() in blob)
    delta = -0.08 * hits
    return min(1.0, max(0.0, base_conf + delta)), hits


def apply_subject_regex_boost(
    base_conf: float, subject: str, regexes: List[re.Pattern]
) -> Tuple[float, int]:
    if not regexes:
        return base_conf, 0
    hit = any(r.search(subject or "") for r in regexes)
    delta = 0.2 if hit else 0.0
    return min(1.0, max(0.0, base_conf + delta)), (1 if hit else 0)


# =========================
# אימות PDF — PyMuPDF תחילה
# =========================

INV_TOKENS_HE = [
    x.lower() for x in (KEYWORDS["hebrew_core"] + KEYWORDS["hebrew_context"])
]
INV_TOKENS_EN = [
    x.lower() for x in (KEYWORDS["english_core"] + KEYWORDS["english_context"])
]
STRICT_KEYWORDS = [
    "חשבונית",
    "חשבונית מס",
    "חשבונית מס קבלה",
    "קבלה",
    "invoice",
    "tax invoice",
    "receipt",
]


def extract_pdf_text_first_pages(path: str, max_pages: int = 2) -> str:
    want = globals().get("PDF_ENGINE", "auto")
    use_pymupdf = (want in ("auto", "pymupdf")) and HAS_PYMUPDF
    if use_pymupdf:
        try:
            doc = fitz.open(path)
            pages = min(len(doc), max_pages)
            parts = []
            flags = fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE
            for i in range(pages):
                try:
                    page = doc.load_page(i)
                    parts.append(page.get_text("text", flags=flags) or "")
                except Exception:
                    continue
            doc.close()
            txt = "\n".join(parts).strip()
            if txt:
                return txt
        except Exception:
            pass
    use_pypdf = (want in ("auto", "pypdf")) and HAS_PYPDF
    if use_pypdf:
        try:
            reader = PdfReader(path)
            pages = min(len(reader.pages), max_pages)
            txt = []
            for i in range(pages):
                try:
                    txt.append(reader.pages[i].extract_text() or "")
                except Exception:
                    continue
            return "\n".join(txt)
        except Exception:
            return ""
    return ""


def text_invoice_score(text: str) -> float:
    if not text:
        return 0.0
    t = text.lower()
    strong = any(k.lower() in t for k in STRICT_KEYWORDS)
    he_hits = sum(1 for k in INV_TOKENS_HE if k in t)
    en_hits = sum(1 for k in INV_TOKENS_EN if k in t)
    score = (
        (0.5 if strong else 0.0) + min(0.3, he_hits * 0.03) + min(0.2, en_hits * 0.02)
    )
    return min(1.0, score)


def verify_pdf_is_invoice(
    path: str, *, threshold: float, min_size: int = DEFAULTS["min_pdf_size_bytes"]
) -> Tuple[bool, Dict[str, Any]]:
    try:
        sz = os.path.getsize(path)
    except Exception:
        return False, {"reason": "no_file"}
    if sz < min_size:
        return False, {"reason": f"too_small({sz}< {min_size})"}
    if threshold <= 0.0:  # מצב none
        return True, {"size": sz, "text_score": None, "mode": "none"}
    txt = extract_pdf_text_first_pages(path, max_pages=3)
    score = text_invoice_score(txt)
    ok = score >= threshold
    return ok, {"size": sz, "text_score": round(score, 3), "threshold": threshold}


# =========================
# הורדות מהלינקים (PDF בלבד)
# =========================


def find_pdf_links_in_html(html: str, base: str) -> List[str]:
    out = []
    if not html:
        return out
    if HAS_BS4:
        try:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all(["a", "iframe", "embed"]):
                url = tag.get("href") or tag.get("src")
                if not url:
                    continue
                full = urljoin(base, url)
                if full.lower().endswith(".pdf"):
                    out.append(full)
        except Exception:
            pass
    else:
        candidates = re.findall(
            r'href=["\']([^"\']+)["\']|src=["\']([^"\']+)', html, re.I
        )
        for a, b in candidates:
            url = a or b
            full = urljoin(base, url)
            if full.lower().endswith(".pdf"):
                out.append(full)
    return list(dict.fromkeys(out))


def requests_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {"User-Agent": "Mozilla/5.0 (InvoiceFetcher/1.0)", "Accept": "*/*"}
    )
    return s


def download_pdf_from_url(
    sess: requests.Session, url: str, out_path: str, *, accept_octet: bool = False
) -> Tuple[bool, str, Dict[str, Any]]:
    try:
        with sess.get(
            url, stream=True, allow_redirects=True, timeout=DEFAULTS["http_timeout"]
        ) as r:
            ct = (r.headers.get("Content-Type") or "").lower()
            if r.status_code >= 400:
                return False, f"http_{r.status_code}", {"ct": ct}
            is_pdf_ct = "application/pdf" in ct
            is_octet = "application/octet-stream" in ct
            if not (
                is_pdf_ct or url.lower().endswith(".pdf") or (accept_octet and is_octet)
            ):
                return False, "not_pdf", {"ct": ct}
            ensure_dir(os.path.dirname(out_path))
            total = 0
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
            if total < DEFAULTS["min_pdf_size_bytes"]:
                try:
                    os.remove(out_path)
                except Exception:
                    pass
                return False, "too_small", {"bytes": total}
            return True, "ok", {"bytes": total, "ct": ct}
    except Exception as e:
        return False, "exc", {"err": str(e)}


def fetch_invoice_from_link(
    sess: requests.Session,
    url: str,
    trusted: List[str],
    allowed_http: List[str],
    base_dir: str,
    msg_id: str,
    idx: int,
    *,
    verify_threshold: float,
    accept_octet: bool,
) -> Tuple[Optional[str], Dict[str, Any]]:
    u = url.strip()
    dom = domain_of(u)
    is_https = u.lower().startswith("https://")
    if not is_https and not (
        u.lower().startswith("http://") and is_http_allowed(dom, allowed_http)
    ):
        return None, {"skip": "insecure_http"}
    fn_base = safe_filename(f"{msg_id}_{dom}_{idx}")
    pdf_out = os.path.join(base_dir, f"{fn_base}.pdf")

    ok, why, meta = download_pdf_from_url(sess, u, pdf_out, accept_octet=accept_octet)
    if ok:
        ok2, meta2 = verify_pdf_is_invoice(pdf_out, threshold=verify_threshold)
        if ok2:
            return pdf_out, {"download": meta, "verify": meta2, "mode": "direct_pdf"}
        else:
            try:
                os.remove(pdf_out)
            except Exception:
                pass
            return None, {"reject": f"verify_fail:{meta2}"}

    if why in ("not_pdf", "ok"):
        try:
            r = sess.get(u, allow_redirects=True, timeout=DEFAULTS["http_timeout"])
            ct = (r.headers.get("Content-Type") or "").lower()
            if r.status_code >= 400:
                return None, {"skip": f"html_http_{r.status_code}"}
            if "text/html" not in ct:
                return None, {"skip": f"html_unexpected_ct:{ct}"}
            pdf_links = find_pdf_links_in_html(r.text or "", r.url)
            for j, p in enumerate(pdf_links, start=1):
                fn_base2 = safe_filename(f"{msg_id}_{domain_of(p)}_{idx}_{j}")
                out2 = os.path.join(base_dir, f"{fn_base2}.pdf")
                ok3, why3, meta3 = download_pdf_from_url(
                    sess, p, out2, accept_octet=accept_octet
                )
                if ok3:
                    ok4, meta4 = verify_pdf_is_invoice(out2, threshold=verify_threshold)
                    if ok4:
                        return out2, {
                            "download": meta3,
                            "verify": meta4,
                            "mode": "html_found_pdf",
                            "from": r.url,
                        }
                    else:
                        try:
                            os.remove(out2)
                        except Exception:
                            pass
            return None, {"reject": "no_pdf_found_in_html"}
        except Exception as e:
            return None, {"skip": f"html_exc:{e}"}

    return None, {"reject": why, **meta}


# =========================
# בניית ביטוי ספקים דינמי
# =========================


def build_provider_aqs(domains: List[str]) -> str:
    parts = [f'"{d}"' for d in domains if d]
    if not parts:
        return '""'
    return "(" + " OR ".join(parts) + ")"


# =========================
# Main
# =========================


def main():
    p = argparse.ArgumentParser(
        description="Find & download invoice PDFs (Heb/Eng) via Microsoft Graph"
    )
    p.add_argument("--client-id", required=True)
    p.add_argument(
        "--authority",
        default="common",
        help="Tenant: common | consumers | organizations | <tenant-id>",
    )
    p.add_argument("--lookback-days", type=int, default=DEFAULTS["lookback_days"])
    p.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="UTC אם אין טיימזון. דוגמה: 2025-09-01 או 2025-09-01T00:00:00Z",
    )
    p.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="סוף טווח (בלעדי). דוגמה: 2025-10-01 או 2025-10-01T03:00:00+03:00",
    )
    p.add_argument("--max-pages", type=int, default=DEFAULTS["max_pages"])
    p.add_argument("--page-size", type=int, default=DEFAULTS["page_size_search"])
    p.add_argument("--min-confidence", type=float, default=DEFAULTS["min_confidence"])

    # פלט תוצאות חיפוש
    p.add_argument("--out-json", default=None)
    p.add_argument("--out-csv", default=None)

    # הורדות
    p.add_argument(
        "--invoices-dir",
        required=False,
        help="תיקייה סופית – רק חשבוניות מאומתות יישמרו כאן. אם לא יוגדר, תיווצר אחת עם timestamp.",
    )
    p.add_argument(
        "--keep-quarantine",
        action="store_true",
        help="שמור קבצים שנדחו (לא חשבוניות) בתיקיית quarantine/ לצורך דיבוג.",
    )
    p.add_argument(
        "--download-timeout",
        type=int,
        default=DEFAULTS["http_timeout"],
        help="timeout להורדות HTTP(S) בשניות.",
    )

    # ניטור/דיבוג
    p.add_argument("--debug", action="store_true")
    p.add_argument("--explain", action="store_true")
    p.add_argument("--save-candidates", default=None)
    p.add_argument("--save-nonmatches", default=None)
    p.add_argument("--threshold-sweep", default=None)

    # כיוונונים
    p.add_argument("--negative-keywords", default=None)
    p.add_argument(
        "--sender-boost", default=None, help="'+@good.com,-@bad.com,+exact@addr.com'"
    )
    p.add_argument(
        "--sender-boost-mode", choices=["extend", "replace"], default="extend"
    )
    p.add_argument("--subject-regex", default=None)
    p.add_argument("--providers", default=None)
    p.add_argument("--providers-mode", choices=["extend", "replace"], default="extend")
    p.add_argument("--allow-http-providers", default=None)

    # מנוע PDF
    p.add_argument(
        "--pdf-engine",
        choices=["auto", "pymupdf", "pypdf"],
        default="auto",
        help="בחירת מנוע חילוץ טקסט מ-PDF: pymupdf | pypdf | auto (ברירת מחדל: auto)",
    )

    # אימות חשבונית
    p.add_argument(
        "--verify",
        choices=["none", "light", "strict"],
        default="strict",
        help="מצב אימות PDF: none (ללא), light (סף נמוך), strict (סף גבוה, דיפולט).",
    )
    p.add_argument(
        "--verify-threshold",
        type=float,
        default=None,
        help="עקיפה ידנית של סף אימות טקסט (override ל-light/strict).",
    )

    # לינקים
    p.add_argument(
        "--accept-octet-stream",
        action="store_true",
        help="החשבת application/octet-stream כלעוד הדומיין מותר/מהימן.",
    )

    args = p.parse_args()

    global DEBUG, PDF_ENGINE
    DEBUG = args.debug
    PDF_ENGINE = args.pdf_engine

    # מנועי PDF
    if PDF_ENGINE == "pymupdf" and not HAS_PYMUPDF:
        print(
            "⚠️ PyMuPDF (fitz) לא מותקן — מבצע נפילה ל-PyPDF2 (אם זמין).",
            file=sys.stderr,
        )
        if HAS_PYPDF:
            PDF_ENGINE = "pypdf"
        else:
            PDF_ENGINE = "auto"
    if PDF_ENGINE == "pypdf" and not HAS_PYPDF:
        print("⚠️ PyPDF2 לא מותקן — מבצע נפילה ל-PyMuPDF (אם זמין).", file=sys.stderr)
        if HAS_PYMUPDF:
            PDF_ENGINE = "pymupdf"
        else:
            PDF_ENGINE = "auto"

    if args.download_timeout:
        DEFAULTS["http_timeout"] = args.download_timeout

    # התחברות
    gc = GraphClient(
        client_id=args.client_id,
        authority=f"https://login.microsoftonline.com/{args.authority}",
    )
    gc.login()

    # חלון תאריכים
    start_dt = parse_user_date_safe("--start-date", args.start_date)
    end_dt = parse_user_date_safe("--end-date", args.end_date)
    validate_date_window(start_dt, end_dt)
    now = now_utc()
    if start_dt and not end_dt:
        end_dt = now
    elif end_dt and not start_dt:
        start_dt = end_dt - dt.timedelta(days=DEFAULTS["lookback_days"])
    elif not start_dt and not end_dt:
        end_dt = now
        start_dt = now - dt.timedelta(days=DEFAULTS["lookback_days"])

    # ספקים + HTTP
    trusted = LINK_RULES["trusted_providers"][:]
    if args.providers:
        user_providers = [
            d.strip().lower() for d in args.providers.split(",") if d.strip()
        ]
        if args.providers_mode == "replace":
            trusted = user_providers
        else:
            trusted = sorted(set(trusted + user_providers))
    allowed_http = LINK_RULES["allowed_http_providers"][:]
    if args.allow_http_providers:
        more = [
            d.strip().lower() for d in args.allow_http_providers.split(",") if d.strip()
        ]
        allowed_http = sorted(set(allowed_http + more))

    # שולח
    sender_rules = DEFAULT_SENDER_BOOST[:]
    if args.sender_boost:
        cli_rules = [w.strip() for w in args.sender_boost.split(",") if w.strip()]
        if args.sender_boost_mode == "replace":
            sender_rules = cli_rules
        else:
            seen_tokens = set(sender_rules)
            for r in cli_rules:
                if r not in seen_tokens:
                    sender_rules.append(r)
                    seen_tokens.add(r)

    negatives = [
        w.strip().lower()
        for w in (args.negative_keywords or "").split(",")
        if w.strip()
    ]

    subject_regexes = []
    if args.subject_regex:
        for pat in args.subject_regex.split(","):
            pat = pat.strip()
            if not pat:
                continue
            try:
                subject_regexes.append(re.compile(pat, re.I))
            except re.error as e:
                print(f"Warning: invalid regex '{pat}': {e}")

    # עדכון אסטרטגיית ספקים
    for s in STRATEGIES:
        if s["name"] == "provider_whitelist_bump":
            s["search"] = build_provider_aqs(trusted)
            break

    # verify threshold
    verify_mode = args.verify
    verify_threshold = (
        args.verify_threshold
        if args.verify_threshold is not None
        else VERIFY_DEFAULTS[verify_mode]
    )

    # הרצת אסטרטגיות
    seen: Dict[str, Dict] = {}
    strat_candidate_counts = Counter()
    strat_desc_map = {}
    for strat in STRATEGIES:
        print(f"Running strategy: {strat['name']} — {strat['description']}")
        msgs = run_strategy(
            gc,
            strategy=strat,
            page_size=args.page_size,
            max_pages=args.max_pages,
            select_fields=DEFAULTS["select_fields"],
        )
        strat_candidate_counts[strat["name"]] += len(msgs)
        strat_desc_map[strat["name"]] = strat["description"]
        for m in msgs:
            mid = m.get("id")
            if mid and mid not in seen:
                seen[mid] = m

    print(f"Candidates fetched (unique by id): {len(seen)}")

    if args.save_candidates:
        with open(args.save_candidates, "w", encoding="utf-8") as f:
            json.dump(list(seen.values()), f, ensure_ascii=False, indent=2)
        print(f"Saved raw candidates: {os.path.abspath(args.save_candidates)}")

    # תיקיות
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    invoices_dir = args.invoices_dir or f"invoices_final_{ts}"
    ensure_dir(invoices_dir)
    quarantine_dir = os.path.join(invoices_dir, "quarantine")
    if args.keep_quarantine:
        ensure_dir(quarantine_dir)

    rows: List[Dict] = []
    nonmatches: List[Dict] = []
    strat_final_counts = Counter()

    download_log: Dict[str, Any] = {
        "invoices_dir": os.path.abspath(invoices_dir),
        "pdf_engine_effective": PDF_ENGINE,
        "pdf_engine_available": {"pymupdf": HAS_PYMUPDF, "pypdf": HAS_PYPDF},
        "verify": {"mode": verify_mode, "threshold": verify_threshold},
        "saved": [],
        "rejected": [],
    }

    sess = requests_session()
    accept_octet = args.accept_octet_stream

    # עיבוד מועמדים
    for mid, msg in seen.items():
        rdt_raw = msg.get("receivedDateTime")
        try:
            rdt = dt.datetime.fromisoformat(rdt_raw.replace("Z", "+00:00"))
        except Exception:
            rdt = None
        if rdt is None or rdt < start_dt or rdt >= end_dt:
            continue

        body = msg.get("body") or {}
        body_text = body_as_text(body)
        urls = extract_urls_from_body(body)
        kept_links, link_score = score_links(
            urls, trusted_providers=trusted, allowed_http_providers=allowed_http
        )

        # מטא־דאטה של צרופות (לניקוד)
        attach_hits: List[Dict] = []
        if msg.get("hasAttachments"):
            try:
                for a in fetch_attachments(gc, mid, want_content=False):
                    if prefers_attachment(a.get("name", ""), a.get("contentType", "")):
                        attach_hits.append(a)
            except Exception as e:
                attach_hits.append({"error": f"attachments_fetch_failed: {e}"})

        lang_score, lang_hits = language_confidence(
            subject=msg.get("subject") or "",
            preview=msg.get("bodyPreview") or "",
            body_text=body_text,
        )

        row = build_row(
            msg,
            kept_links,
            attach_hits,
            lang_score,
            link_score,
            lang_hits,
            include_explain=args.explain,
            body_text_for_explain=body_text,
        )
        conf = row["match_confidence"]
        subj = row["subject"]

        conf += subject_strong_bonus(subj)
        conf += donation_bonus(subj)
        muni_bonus, _ = municipal_attachment_bonus(subj, attach_hits)
        conf = min(1.0, conf + muni_bonus)
        penalty = attachment_notice_penalty(attach_hits)
        conf = min(1.0, max(0.0, conf + penalty))
        conf = apply_sender_boost(conf, msg.get("from") or {}, sender_rules)
        conf, _ = apply_negative_keywords(
            conf, subj, msg.get("bodyPreview") or "", body_text, negatives
        )
        conf, _ = apply_subject_regex_boost(conf, subj, subject_regexes)
        row["match_confidence"] = round(conf, 3)

        if conf < args.min_confidence:
            if args.save_nonmatches:
                nonmatches.append(row)
            continue

        saved_any_for_msg = False

        # ===== הורדת צרופות (עם תוכן) =====
        if msg.get("hasAttachments"):
            try:
                full_atts = fetch_attachments(gc, mid, want_content=True)
                for a in full_atts:
                    name = a.get("name") or f"attachment_{a.get('id')}.bin"
                    ct = (a.get("contentType") or "").lower()
                    cb = a.get("contentBytes")
                    if not cb:
                        continue
                    raw = base64.b64decode(cb)
                    out_path = os.path.join(invoices_dir, safe_filename(name))
                    is_pdf = (ct == "application/pdf") or name.lower().endswith(".pdf")
                    if is_pdf:
                        tmp_path = os.path.join(
                            invoices_dir, f"._tmp_{safe_filename(name)}"
                        )
                        with open(tmp_path, "wb") as f:
                            f.write(raw)
                        ok, meta = verify_pdf_is_invoice(
                            tmp_path, threshold=verify_threshold
                        )
                        if ok:
                            os.replace(tmp_path, out_path)
                            download_log["saved"].append(
                                {
                                    "msg_id": mid,
                                    "type": "attachment",
                                    "path": out_path,
                                    "verify": meta,
                                }
                            )
                            saved_any_for_msg = True
                        else:
                            if args.keep_quarantine:
                                qpath = os.path.join(
                                    quarantine_dir, safe_filename(name)
                                )
                                os.replace(tmp_path, qpath)
                                download_log["rejected"].append(
                                    {
                                        "msg_id": mid,
                                        "type": "attachment",
                                        "path": qpath,
                                        "reason": meta,
                                    }
                                )
                            else:
                                try:
                                    os.remove(tmp_path)
                                except Exception:
                                    pass
                    else:
                        if args.keep_quarantine:
                            qpath = os.path.join(quarantine_dir, safe_filename(name))
                            with open(qpath, "wb") as f:
                                f.write(raw)
                            download_log["rejected"].append(
                                {
                                    "msg_id": mid,
                                    "type": "attachment_non_pdf",
                                    "path": qpath,
                                    "reason": {"ct": ct},
                                }
                            )
            except Exception as e:
                download_log["rejected"].append(
                    {"msg_id": mid, "type": "attachment_error", "reason": str(e)}
                )

        # ===== הורדת לינקים =====
        for idx, url in enumerate(kept_links, start=1):
            file_path, info = fetch_invoice_from_link(
                sess,
                url,
                trusted=trusted,
                allowed_http=allowed_http,
                base_dir=invoices_dir,
                msg_id=mid,
                idx=idx,
                verify_threshold=verify_threshold,
                accept_octet=accept_octet,
            )
            if file_path:
                download_log["saved"].append(
                    {
                        "msg_id": mid,
                        "type": "link",
                        "url": url,
                        "path": file_path,
                        **info,
                    }
                )
                saved_any_for_msg = True
            else:
                download_log["rejected"].append(
                    {"msg_id": mid, "type": "link", "url": url, **info}
                )

        if saved_any_for_msg:
            rows.append(row)
            strat_final_counts[row["matched_strategy"]] += 1
        else:
            if args.save_nonmatches:
                nonmatches.append(row)

    # ---- פלטי חיפוש ----
    rows.sort(key=lambda r: r["receivedDateTime"] or "", reverse=True)
    ts2 = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = args.out_json or f"invoice_messages_{ts2}.json"
    out_csv = args.out_csv or f"invoice_messages_{ts2}.csv"
    out_summary_csv = f"invoices_summary_{ts2}.csv"
    download_report_json = os.path.join(invoices_dir, "download_report.json")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    def flatten(x):
        if isinstance(x, list):
            return "; ".join(
                json.dumps(i, ensure_ascii=False) if isinstance(i, dict) else str(i)
                for i in x
            )
        return x

    csv_rows = [
        {
            "id": r["id"],
            "subject": r["subject"],
            "from": r["from"],
            "receivedDateTime": r["receivedDateTime"],
            "hasAttachments": r["hasAttachments"],
            "matched_strategy": r["matched_strategy"],
            "matched_strategy_description": r["matched_strategy_description"],
            "match_confidence": r["match_confidence"],
            "lang_hits_he": r["lang_hits_he"],
            "lang_hits_en": r["lang_hits_en"],
            "matched_links": flatten(r["matched_links"]),
            "matched_attachments": flatten(r["matched_attachments"]),
            "webLink": r["webLink"],
        }
        for r in rows
    ]
    pd.DataFrame(csv_rows).to_csv(out_csv, index=False, encoding="utf-8")

    if args.save_nonmatches:
        with open(args.save_nonmatches, "w", encoding="utf-8") as f:
            json.dump(nonmatches, f, ensure_ascii=False, indent=2)
        print(f"Saved nonmatches: {os.path.abspath(args.save_nonmatches)}")

    # סיכום אסטרטגיות
    win_str = f"{start_dt.isoformat()} → {end_dt.isoformat()} (UTC, end exclusive)"
    print(f"\nStrategy summary (window={win_str}, min_conf={args.min_confidence:.2f}):")
    print("-" * 100)
    print(f"{'strategy':32} | {'candidates':10} | {'final_matches':13} | description")
    print("-" * 100)
    summary_rows = []
    for s in STRATEGIES:
        name = s["name"]
        cand = strat_candidate_counts.get(name, 0)
        fin = strat_final_counts.get(name, 0)
        desc = strat_desc_map.get(name, "")
        print(f"{name:32} | {cand:10d} | {fin:13d} | {desc}")
        summary_rows.append(
            {
                "strategy": name,
                "candidates": cand,
                "final_matches": fin,
                "description": desc,
                "window_utc": win_str,
            }
        )
    pd.DataFrame(summary_rows).to_csv(out_summary_csv, index=False, encoding="utf-8")

    # דו"ח הורדות
    with open(download_report_json, "w", encoding="utf-8") as f:
        json.dump(download_log, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(rows)} messages that yielded verified invoices")
    print(f"Final invoices dir: {os.path.abspath(invoices_dir)}")
    print(f"Download report: {os.path.abspath(download_report_json)}")
    print(f"JSON: {os.path.abspath(out_json)}")
    print(f"CSV : {os.path.abspath(out_csv)}")
    print(f"Summary: {os.path.abspath(out_summary_csv)}")
    if args.keep_quarantine:
        print(f"Quarantine kept under: {os.path.abspath(quarantine_dir)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
