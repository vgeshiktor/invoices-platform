#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Graph Invoice Finder (v3.6.2)
שיפורים עיקריים:
- $search תקין עבור דומיינים: כל דומיין במירכאות, ובניית ביטוי דינמית מרשימת trusted providers.
- בדיקות קלט ידידותיות ל- --start-date/--end-date עם הודעות ברורות.
- כולל תוספות v3.6: אסטרטגיית עיריות/ארנונה, HTTP מותר לדומיינים מוגדרים, בונוס לצרופות PDF מספריות, בוסט לשולחים (כולל ברירת-מחדל לבזק), כלי אימות/ניטור.

הערה: משתמשים ב-$search בלבד (ללא $filter/$orderby/$count) כדי להימנע מ-SearchWithFilter/InefficientFilter.
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

import msal
import pandas as pd
import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.Read"]

DEBUG = False  # מוגדר מ-CLI

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
}

# ברירת־מחדל: בוסט לשולח בזק
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
    # מילות מפתח לעיריות/ארנונה
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
}

ATTACHMENT_PREF = {
    "extensions": [".pdf", ".tif", ".tiff", ".jpg", ".jpeg", ".png", ".xlsx", ".xls"],
    "name_hints": ["invoice", "receipt", "חשבונית", "קבלה", "שובר", "ארנונה"],
}

LINK_RULES = {
    "require_https": True,  # ניתן לעקוף באמצעות רשימת HTTP מותר
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
        "gov.il",
        "freshbooks.com",
        "waveapps.com",
        "bezeq.co.il",
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
        "file_like_suffixes": [".pdf", ".html", ".aspx"],
    },
    # דומיינים עם HTTP מותר (ללא https)
    "allowed_http_providers": ["citypay.co.il"],
}

LANG_WEIGHTS = {"he": 1.2, "en": 1.0}

# =========================
# אסטרטגיות (AQS) — ללא $filter/$orderby/$count!
# =========================

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
    # provider_whitelist_bump יעודכן דינמית אחרי חישוב trusted
    {
        "name": "provider_whitelist_bump",
        "description": "כיוון לספקים מוכרים (GreenInvoice, iCount, QuickBooks, Stripe, gov.il) המופיעים בטקסט/לינקים.",
        "search": '("greeninvoice.co.il" OR "icount.co.il" OR "ezcount.co.il" OR "quickbooks.intuit.com" OR "stripe.com" OR "paypal.com" OR "zoho.com" OR "xero.com" OR "shopify.com" OR "tax.gov.il")',
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
    """YYYY-MM-DD או ISO8601; אם נאיבי — UTC."""
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
        m = re.findall(r"https?://([^/]+)/?|http://([^/]+)/?", url, re.I)
        host = (m[0][0] or m[0][1]) if m else ""
        return re.sub(r"^www\.", "", host).lower()
    except Exception:
        try:
            return re.sub(
                r"^www\.", "", re.findall(r"://([^/]+)/?", url, re.I)[0]
            ).lower()
        except Exception:
            return ""


def path_of(url: str) -> str:
    try:
        return "/" + url.split("/", 3)[3]
    except Exception:
        return ""


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


def score_links(
    urls: List[str], trusted_providers: List[str], allowed_http_providers: List[str]
) -> Tuple[List[str], float]:
    path_patterns = [p.lower() for p in LINK_RULES["heuristics"]["path_patterns"]]
    keywords = [k.lower() for k in LINK_RULES["url_keywords"]]
    suffixes = [s.lower() for s in LINK_RULES["heuristics"]["file_like_suffixes"]]

    kept, score = [], 0.0
    for u in urls:
        u_low = u.lower()
        is_https = u_low.startswith("https://")
        if not is_https:
            if not (
                u_low.startswith("http://")
                and is_http_allowed(domain_of(u), allowed_http_providers)
            ):
                continue

        dom = domain_of(u)
        path = path_of(u).lower()

        trust = is_trusted_domain(dom, trusted_providers)
        has_kw = any(k in u_low for k in keywords)
        has_pat = any(p in path for p in path_patterns)
        has_suf = any(u_low.endswith(s) or f"?{s}" in u_low for s in suffixes)

        if trust or has_kw or has_pat or has_suf:
            kept.append(u)
            if trust:
                score += 0.3
            if has_suf:
                score += 0.2
            if has_kw or has_pat:
                score += 0.1

    return kept, min(score, 0.8)


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
    score = hits_he * LANG_WEIGHTS["he"] * 0.05 + hits_en * LANG_WEIGHTS["en"] * 0.05
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


def municipal_attachment_bonus(
    subject: str, attachments: List[Dict]
) -> Tuple[float, Dict[str, Any]]:
    """
    בונוס חכם: אם הנושא מרמז על עירייה/ארנונה/שובר, ויש PDF עם שם מספרי "נקי".
    """
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
    """
    עם $search בלבד: לא מוסיפים $filter/$orderby/$count.
    """
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
        next_params = {}  # nextLink כולל את הפרמטרים
    for m in out:
        m["_matched_strategy"] = strategy["name"]
        m["_matched_strategy_description"] = strategy["description"]
    return out


# =========================
# בדיקת תאריכים (קלט ידידותי)
# =========================


def parse_user_date_safe(label: str, s: Optional[str]) -> Optional[dt.datetime]:
    """
    מחזיר datetime או זורק SystemExit עם הודעה ידידותית אם הפורמט לא תקין.
    תומך: YYYY-MM-DD או ISO8601 (כולל Z או offset).
    """
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
# צרופות
# =========================


def fetch_attachments(
    gc: GraphClient, message_id: str, want_content: bool = False
) -> List[Dict]:
    base = f"{GRAPH_BASE}/me/messages/{message_id}/attachments"
    url = base
    attachments: List[Dict] = []
    while url:
        params = {}
        if want_content:
            params["$select"] = "id,name,contentType,size,@odata.type,contentBytes"
        data = gc.get(url, params=params, use_search=False)
        for a in data.get("value", []):
            a_type = a.get("@odata.type", "")
            if a_type.endswith("fileAttachment") or a_type.endswith("itemAttachment"):
                attachments.append(
                    {
                        "id": a.get("id"),
                        "name": a.get("name"),
                        "contentType": a.get("contentType"),
                        "size": a.get("size"),
                        "odata_type": a_type,
                        "contentBytes": a.get("contentBytes") if want_content else None,
                    }
                )
        url = data.get("@odata.nextLink")
    return attachments


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


# =========================
# ניקוד דינמי
# =========================


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
# בניית חיפוש ספקים דינמי
# =========================


def build_provider_aqs(domains: List[str]) -> str:
    """
    מחזיר ביטוי AQS כמו: ("a.com" OR "b.com" OR "c.co.il")
    מצטט כל דומיין כדי לאפשר תווים כמו '.'.
    """
    parts = [f'"{d}"' for d in domains if d]
    if not parts:
        return '""'  # ביטוי ריק בטוח
    return "(" + " OR ".join(parts) + ")"


# =========================
# Main
# =========================


def main():
    p = argparse.ArgumentParser(
        description="Find invoice/receipt emails (Heb/Eng) via Microsoft Graph"
    )
    p.add_argument(
        "--client-id", required=True, help="Entra public client application ID"
    )
    p.add_argument(
        "--authority",
        default="common",
        help="Tenant: common | consumers | organizations | <tenant-id>",
    )
    p.add_argument(
        "--lookback-days",
        type=int,
        default=DEFAULTS["lookback_days"],
        help="בשימוש רק אם אין start/end מלאים.",
    )
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
    p.add_argument(
        "--page-size",
        type=int,
        default=DEFAULTS["page_size_search"],
        help="גודל עמוד ל-$search",
    )
    p.add_argument("--min-confidence", type=float, default=DEFAULTS["min_confidence"])
    p.add_argument("--out-json", default=None, help="קובץ JSON פלט")
    p.add_argument("--out-csv", default=None, help="קובץ CSV פלט")

    # אימות/ניטור
    p.add_argument("--debug", action="store_true", help="לוג מפורט")
    p.add_argument("--explain", action="store_true", help="להוסיף הסברים לכל שורה")
    p.add_argument(
        "--save-candidates", default=None, help="לשמור את כל המועמדים הגולמיים JSON"
    )
    p.add_argument("--save-nonmatches", default=None, help="לשמור פריטים שנדחו JSON")
    p.add_argument(
        "--threshold-sweep", default=None, help="בדיקת ספים, למשל: 0.30,0.40,0.55,0.70"
    )

    # כיוונונים
    p.add_argument(
        "--negative-keywords",
        default=None,
        help="מילות שלילה להורדת ניקוד (מופרדות בפסיקים).",
    )
    p.add_argument(
        "--sender-boost",
        default=None,
        help="'+@good.com,-@bad.com,+exact@addr.com' מופרד בפסיקים.",
    )
    p.add_argument(
        "--sender-boost-mode",
        choices=["extend", "replace"],
        default="extend",
        help="extend ברירת־מחדל: להרחיב את רשימת הבוסט הדיפולטית.",
    )
    p.add_argument(
        "--subject-regex",
        default=None,
        help="ביטויי רג׳קס לנושא; בונוס אם יש התאמה (מופרד בפסיקים).",
    )
    p.add_argument(
        "--providers",
        default=None,
        help="דומיינים להרחיב/להחליף את רשימת הספקים המהימנים.",
    )
    p.add_argument(
        "--providers-mode",
        choices=["extend", "replace"],
        default="extend",
        help="extend ברירת־מחדל או replace.",
    )
    p.add_argument(
        "--download-attachments",
        default=None,
        help="תיקייה לשמירת צרופות של התאמות סופיות.",
    )

    # HTTP מותר לדומיינים
    p.add_argument(
        "--allow-http-providers",
        default=None,
        help="דומיינים שמותרים ב-http (לא https), מופרדים בפסיקים. מוסיף לברירת־המחדל.",
    )

    args = p.parse_args()

    global DEBUG
    DEBUG = args.debug

    # התחברות
    gc = GraphClient(
        client_id=args.client_id,
        authority=f"https://login.microsoftonline.com/{args.authority}",
    )
    gc.login()

    # חלון תאריכים — בדיקת קלט עם הודעות ידידותיות
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

    # ספקים מהימנים + HTTP מותר
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

    # שולח: דיפולט + הרחבה/החלפה
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

    # עדכון דינמי של אסטרטגיית ספקים — כל הדומיינים במירכאות
    for s in STRATEGIES:
        if s["name"] == "provider_whitelist_bump":
            s["search"] = build_provider_aqs(trusted)
            break

    # הרצת אסטרטגיות ואיחוד תוצאות
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

    rows: List[Dict] = []
    nonmatches: List[Dict] = []
    strat_final_counts = Counter()

    download_dir = args.download_attachments
    if download_dir:
        os.makedirs(download_dir, exist_ok=True)

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

        # בונוס חכם לצרופות+נושא עירוני
        muni_bonus, muni_info = municipal_attachment_bonus(row["subject"], attach_hits)
        conf = min(1.0, conf + muni_bonus)
        if args.explain:
            row.setdefault("explanations", {})["municipal_bonus"] = {
                "bonus": round(muni_bonus, 3),
                **muni_info,
            }

        # Sender boost
        conf = apply_sender_boost(conf, msg.get("from") or {}, sender_rules)

        # Negative keywords
        conf, neg_hits = apply_negative_keywords(
            conf, row["subject"], msg.get("bodyPreview") or "", body_text, negatives
        )
        if args.explain:
            row.setdefault("explanations", {})["negatives"] = {
                "hits": neg_hits,
                "applied": bool(neg_hits),
            }

        # Subject regex
        conf, subj_hits = apply_subject_regex_boost(
            conf, row["subject"], subject_regexes
        )
        if args.explain:
            row.setdefault("explanations", {})["subject_regex"] = {
                "matched": bool(subj_hits),
                "patterns": [r.pattern for r in subject_regexes],
            }

        row["match_confidence"] = round(conf, 3)

        if conf >= args.min_confidence:
            rows.append(row)
            strat_final_counts[row["matched_strategy"]] += 1

            if download_dir and attach_hits:
                try:
                    full_atts = fetch_attachments(gc, mid, want_content=True)
                    for a in full_atts:
                        if not prefers_attachment(a.get("name"), a.get("contentType")):
                            continue
                        cb = a.get("contentBytes")
                        if not cb:
                            continue
                        try:
                            data_bytes = base64.b64decode(cb)
                        except Exception:
                            continue
                        safe_mid = mid.replace("/", "_")
                        subdir = os.path.join(download_dir, safe_mid)
                        os.makedirs(subdir, exist_ok=True)
                        fname = a.get("name") or f"attachment_{a.get('id')}.bin"
                        path = os.path.join(subdir, fname)
                        with open(path, "wb") as f:
                            f.write(data_bytes)
                        if args.explain:
                            row.setdefault("explanations", {}).setdefault(
                                "downloaded", []
                            ).append(path)
                except Exception as e:
                    if args.explain:
                        row.setdefault("explanations", {})["download_error"] = str(e)
        else:
            if args.save_nonmatches:
                nonmatches.append(row)

    rows.sort(key=lambda r: r["receivedDateTime"] or "", reverse=True)

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = args.out_json or f"invoice_messages_{ts}.json"
    out_csv = args.out_csv or f"invoice_messages_{ts}.csv"
    out_summary_csv = f"invoices_summary_{ts}.csv"

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

    if args.threshold_sweep:
        tests = [float(x) for x in args.threshold_sweep.split(",") if x.strip()]
        print("\nThreshold sweep on FINAL rows:")
        for t in tests:
            c = sum(1 for r in rows if r["match_confidence"] >= t)
            print(f"  >= {t:.2f}: {c} rows")

    print(f"\nSaved {len(rows)} matches")
    print(f"JSON: {os.path.abspath(out_json)}")
    print(f"CSV : {os.path.abspath(out_csv)}")
    print(f"Summary: {os.path.abspath(out_summary_csv)}")
    if args.download_attachments:
        print(
            f"Attachments (if any) saved under: {os.path.abspath(args.download_attachments)}"
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
