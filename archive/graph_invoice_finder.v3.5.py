#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Graph Invoice Finder (v3.5)
- $search-only requests (no $filter/$orderby/$count) to avoid SearchWithFilter/InefficientFilter
- Client-side date window: --start-date/--end-date or --lookback-days
- Strategy descriptions + per-strategy summary table
- Validation tooling: --explain --debug --save-candidates --save-nonmatches --threshold-sweep
- Tuning knobs:
  * --negative-keywords "newsletter,promotion,..." (subtracts score on hits)
  * --sender-boost "+@good.com,-@bad.com,+exact@addr.com" (adjust score by sender/domain)
  * --subject-regex "Invoice\\s*#\\d+,חשבונית(\\s*מס)?\\s*#?\\d+" (boost on match)
  * --providers "domain1,domain2" with --providers-mode extend|replace
  * --download-attachments DIR (saves qualifying attachments for FINAL matches)
Outputs:
  - JSON + CSV of final matches
  - CSV summary table per strategy
"""

import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from html import unescape
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter

import msal
import pandas as pd
import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.Read"]

DEBUG = False  # set from CLI

# =========================
# Configuration
# =========================

DEFAULTS = {
    "select_fields": "id,subject,from,receivedDateTime,hasAttachments,body,bodyPreview,webLink",
    "page_size_search": 50,
    "max_pages": 20,
    "lookback_days": 120,
    "min_confidence": 0.55,
    "timeout_sec": 30,
}

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
}

ATTACHMENT_PREF = {
    "extensions": [".pdf", ".tif", ".tiff", ".jpg", ".jpeg", ".png", ".xlsx", ".xls"],
    "name_hints": ["invoice", "receipt", "חשבונית", "קבלה"],
}

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
        ],
        "file_like_suffixes": [".pdf", ".html", ".aspx"],
    },
}

LANG_WEIGHTS = {"he": 1.2, "en": 1.0}

# Each strategy has a name, description, and $search expression
STRATEGIES = [
    {
        "name": "attachments_and_keywords_recent",
        "description": "Broad English/Hebrew invoice/receipt keywords to catch classic subjects/bodies; attachments handled client-side.",
        "search": '"invoice OR receipt OR חשבונית OR קבלה"',
    },
    {
        "name": "keywords_only_recent",
        "description": "Wider net including ‘statement’/‘billing’/‘תשלום’ to catch link-only invoices and providers that avoid saying ‘invoice’.",
        "search": '"(invoice OR receipt OR statement OR billing OR חשבונית OR קבלה OR תשלום)"',
    },
    {
        "name": "hebrew_bias",
        "description": "Strong bias toward common Hebrew phrases like ‘חשבונית מס’ and ‘חשבונית מס קבלה’ where most emails are expected.",
        "search": r'"(חשבונית OR \"חשבונית מס\" OR קבלה OR תשלום OR \"חשבונית מס קבלה\")"',
    },
    {
        "name": "provider_whitelist_bump",
        "description": "Target known invoice providers (GreenInvoice, iCount, QuickBooks, Stripe, gov.il, etc.) appearing in message bodies/links.",
        "search": '"(greeninvoice.co.il OR icount.co.il OR ezcount.co.il OR quickbooks.intuit.com OR stripe.com OR paypal.com OR zoho.com OR xero.com OR shopify.com OR tax.gov.il)"',
    },
]

# =========================
# Helpers
# =========================


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_any_dt(s: str) -> dt.datetime:
    """Parse YYYY-MM-DD or ISO8601; naive → UTC."""
    if len(s) == 10 and re.match(r"\d{4}-\d{2}-\d{2}$", s):
        d = dt.datetime.strptime(s, "%Y-%m-%d")
        return d.replace(tzinfo=dt.timezone.utc)
    s2 = s.replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(s2)
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


URL_RE = re.compile(r'https?://[^\s<>"\'\]]+', re.IGNORECASE)


def extract_urls_from_body(body: Dict) -> List[str]:
    content = (body or {}).get("content", "") or ""
    txt = unescape(content)
    urls = URL_RE.findall(txt)
    urls = list(dict.fromkeys([u.strip(").,]}>\"'") for u in urls]))
    return urls


def domain_of(url: str) -> str:
    try:
        return re.sub(
            r"^www\.", "", re.findall(r"https?://([^/]+)/?", url, re.I)[0]
        ).lower()
    except Exception:
        return ""


def path_of(url: str) -> str:
    try:
        return "/" + url.split("/", 3)[3]
    except Exception:
        return ""


def email_addr_of_from(frm: Dict) -> Tuple[str, str]:
    """Return (name, email) from message['from']."""
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


def score_links(
    urls: List[str], trusted_providers: List[str]
) -> Tuple[List[str], float]:
    trusted = set(d.lower() for d in trusted_providers)
    path_patterns = [p.lower() for p in LINK_RULES["heuristics"]["path_patterns"]]
    keywords = [k.lower() for k in LINK_RULES["url_keywords"]]
    suffixes = [s.lower() for s in LINK_RULES["heuristics"]["file_like_suffixes"]]

    kept, score = [], 0.0
    for u in urls:
        if LINK_RULES["require_https"] and not u.lower().startswith("https://"):
            continue
        dom = domain_of(u)
        path = path_of(u).lower()
        u_l = u.lower()

        trust = dom in trusted
        has_kw = any(k in u_l for k in keywords)
        has_pat = any(p in path for p in path_patterns)
        has_suf = any(u_l.endswith(s) or f"?{s}" in u_l for s in suffixes)

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
                "Failed to create device flow. Check client id / authority."
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
    With $search: DO NOT include $filter/$orderby/$count (avoid SearchWithFilter & InefficientFilter).
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
        next_params = {}  # nextLink includes params

    for m in out:
        m["_matched_strategy"] = strategy["name"]
        m["_matched_strategy_description"] = strategy["description"]
    return out


def fetch_attachments(
    gc: GraphClient, message_id: str, want_content: bool = False
) -> List[Dict]:
    """Fetch attachments; optionally include contentBytes for file attachments."""
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
        ],  # omit raw bytes in row
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
# Dynamic scoring knobs
# =========================


def apply_sender_boost(base_conf: float, frm: Dict, rules: List[str]) -> float:
    """rules like ['+@good.com','-@bad.com','+exact@addr.com']"""
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
    """Subtract small score if negative keywords appear."""
    if not negatives:
        return base_conf, 0
    blob = f"{subject}\n{preview}\n{body_text}".lower()
    hits = sum(1 for w in negatives if w.strip() and w.lower() in blob)
    delta = -0.08 * hits  # conservative
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
        help="Used only when start/end are not fully provided.",
    )
    p.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Start datetime (UTC if tz not provided). e.g., 2025-07-01 or 2025-07-01T00:00:00+03:00",
    )
    p.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End datetime (exclusive). e.g., 2025-09-30 or 2025-09-30T00:00:00Z",
    )
    p.add_argument("--max-pages", type=int, default=DEFAULTS["max_pages"])
    p.add_argument(
        "--page-size",
        type=int,
        default=DEFAULTS["page_size_search"],
        help="Per-page size for $search calls",
    )
    p.add_argument("--min-confidence", type=float, default=DEFAULTS["min_confidence"])
    p.add_argument("--out-json", default=None, help="Output JSON path")
    p.add_argument("--out-csv", default=None, help="Output CSV path")

    # Validation / debug
    p.add_argument("--debug", action="store_true", help="Verbose HTTP/query logging")
    p.add_argument(
        "--explain", action="store_true", help="Include explanations per row"
    )
    p.add_argument(
        "--save-candidates", default=None, help="Dump ALL raw candidates to JSON"
    )
    p.add_argument(
        "--save-nonmatches", default=None, help="Dump seen-but-rejected items to JSON"
    )
    p.add_argument(
        "--threshold-sweep",
        default=None,
        help="Comma-separated thresholds to test, e.g. 0.30,0.40,0.55,0.70",
    )

    # Tuning knobs
    p.add_argument(
        "--negative-keywords",
        default=None,
        help="Comma-separated keywords to downweight if present (subject/body).",
    )
    p.add_argument(
        "--sender-boost",
        default=None,
        help="Comma-separated list like '+@good.com,-@bad.com,+exact@addr.com'.",
    )
    p.add_argument(
        "--subject-regex",
        default=None,
        help="Comma-separated regex patterns; boost if subject matches any.",
    )
    p.add_argument(
        "--providers",
        default=None,
        help="Comma-separated provider domains to extend/replace trusted list.",
    )
    p.add_argument(
        "--providers-mode",
        choices=["extend", "replace"],
        default="extend",
        help="Extend (default) or replace the trusted provider list with --providers.",
    )
    p.add_argument(
        "--download-attachments",
        default=None,
        help="Directory to save qualifying attachments for FINAL matches.",
    )

    args = p.parse_args()

    # Debug flag
    global DEBUG
    DEBUG = args.debug

    # Auth
    gc = GraphClient(
        client_id=args.client_id,
        authority=f"https://login.microsoftonline.com/{args.authority}",
    )
    gc.login()

    # Compute date window
    now = now_utc()
    start_dt: Optional[dt.datetime] = (
        parse_any_dt(args.start_date) if args.start_date else None
    )
    end_dt: Optional[dt.datetime] = (
        parse_any_dt(args.end_date) if args.end_date else None
    )

    if start_dt and end_dt and end_dt <= start_dt:
        raise SystemExit("--end-date must be later than --start-date.")

    if start_dt and not end_dt:
        end_dt = now
    elif end_dt and not start_dt:
        start_dt = end_dt - dt.timedelta(days=args.lookback_days)
    elif not start_dt and not end_dt:
        end_dt = now
        start_dt = now - dt.timedelta(days=args.lookback_days)

    # Tune: providers
    trusted = LINK_RULES["trusted_providers"][:]
    if args.providers:
        user_providers = [
            d.strip().lower() for d in args.providers.split(",") if d.strip()
        ]
        if args.providers_mode == "replace":
            trusted = user_providers
        else:
            trusted = sorted(set(trusted + user_providers))
    # Parse negatives, sender-boost, subject-regex
    negatives = [
        w.strip().lower()
        for w in (args.negative_keywords or "").split(",")
        if w.strip()
    ]
    sender_rules = [
        w.strip() for w in (args.sender_boost or "").split(",") if w.strip()
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

    # Run all strategies (dedupe by id) + track per-strategy candidate counts
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

    # Optionally dump raw candidates
    if args.save_candidates:
        with open(args.save_candidates, "w", encoding="utf-8") as f:
            json.dump(list(seen.values()), f, ensure_ascii=False, indent=2)
        print(f"Saved raw candidates: {os.path.abspath(args.save_candidates)}")

    # Score + enrich + DATE FILTER (client-side) + track final match counts per strategy
    rows: List[Dict] = []
    nonmatches: List[Dict] = []
    strat_final_counts = Counter()

    # Prepare download dir if requested
    download_dir = args.download_attachments
    if download_dir:
        os.makedirs(download_dir, exist_ok=True)

    for mid, msg in seen.items():
        rdt_raw = msg.get("receivedDateTime")
        try:
            rdt = dt.datetime.fromisoformat(rdt_raw.replace("Z", "+00:00"))
        except Exception:
            rdt = None

        # Apply client-side window: start_dt <= rdt < end_dt
        if rdt is None or rdt < start_dt or rdt >= end_dt:
            continue

        body = msg.get("body") or {}
        body_text = body_as_text(body)
        urls = extract_urls_from_body(body)
        kept_links, link_score = score_links(urls, trusted_providers=trusted)

        attach_hits: List[Dict] = []
        if msg.get("hasAttachments"):
            try:
                # Only fetch names/types now; if download requested, we fetch content later.
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

        # Base row/confidence
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

        # Subject regex boost
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

            # Optional: download attachments for final matches
            if download_dir and attach_hits:
                # Re-fetch with contentBytes
                try:
                    full_atts = fetch_attachments(gc, mid, want_content=True)
                    # Filter to those we "prefer"
                    for a in full_atts:
                        if not prefers_attachment(
                            a.get("name", ""), a.get("contentType", "")
                        ):
                            continue
                        cb = a.get("contentBytes")
                        if not cb:
                            continue
                        try:
                            data_bytes = base64.b64decode(cb)
                        except Exception:
                            continue
                        # Build path
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

    # Sort by date desc (client-side)
    rows.sort(key=lambda r: r["receivedDateTime"] or "", reverse=True)

    # Output filenames
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = args.out_json or f"invoice_messages_{ts}.json"
    out_csv = args.out_csv or f"invoice_messages_{ts}.csv"
    out_summary_csv = f"invoices_summary_{ts}.csv"

    # Write JSON
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    # Write CSV (flatten lists)
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

    # Save nonmatches if requested
    if args.save_nonmatches:
        with open(args.save_nonmatches, "w", encoding="utf-8") as f:
            json.dump(nonmatches, f, ensure_ascii=False, indent=2)
        print(f"Saved nonmatches: {os.path.abspath(args.save_nonmatches)}")

    # Summary table
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

    # Threshold sweep
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
    if download_dir:
        print(f"Attachments (if any) saved under: {os.path.abspath(download_dir)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
