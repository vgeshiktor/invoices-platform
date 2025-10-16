#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Graph Invoice Finder (v3.1)
- FIX: Do NOT combine $search with $filter (SearchWithFilter 400). Date filtering is client-side now.
- Also avoids InefficientFilter by not mixing $search with $orderby/$count.
- Auth: MSAL Device Code (PublicClientApplication)
- Targets: /v1.0/me/messages
- Paginates via @odata.nextLink
- Fetches attachments, extracts & scores invoice links
- Outputs JSON + CSV
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from html import unescape
from typing import Dict, List, Optional, Tuple

import msal
import pandas as pd
import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.Read"]

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

# Strategies now contain ONLY the $search expression.
STRATEGIES = [
    {
        "name": "attachments_and_keywords_recent",
        "search": '"invoice OR receipt OR חשבונית OR קבלה"',
    },
    {
        "name": "keywords_only_recent",
        "search": '"(invoice OR receipt OR statement OR billing OR חשבונית OR קבלה OR תשלום)"',
    },
    {
        "name": "hebrew_bias",
        "search": r'"(חשבונית OR \"חשבונית מס\" OR קבלה OR תשלום OR \"חשבונית מס קבלה\")"',
    },
    {
        "name": "provider_whitelist_bump",
        "search": '"(greeninvoice.co.il OR icount.co.il OR ezcount.co.il OR quickbooks.intuit.com OR stripe.com OR paypal.com OR zoho.com OR xero.com OR shopify.com OR tax.gov.il)"',
    },
]

# =========================
# Helpers
# =========================


def iso_utc_now_minus_days(days: int) -> dt.datetime:
    """Return a timezone-aware UTC datetime for now - days."""
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)


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


def score_links(urls: List[str]) -> Tuple[List[str], float]:
    ld = LINK_RULES
    trusted = set(d.lower() for d in ld["trusted_providers"])
    path_patterns = [p.lower() for p in ld["heuristics"]["path_patterns"]]
    keywords = [k.lower() for k in ld["url_keywords"]]
    suffixes = [s.lower() for s in ld["heuristics"]["file_like_suffixes"]]

    kept, score = [], 0.0
    for u in urls:
        if ld["require_https"] and not u.lower().startswith("https://"):
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
    IMPORTANT:
    - With $search: DO NOT include $filter/$orderby/$count (avoid SearchWithFilter & InefficientFilter).
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
    return out


def fetch_attachments(gc: GraphClient, message_id: str) -> List[Dict]:
    url = f"{GRAPH_BASE}/me/messages/{message_id}/attachments"
    attachments: List[Dict] = []
    while url:
        data = gc.get(url, params={}, use_search=False)
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
                    }
                )
        url = data.get("@odata.nextLink")
    return attachments


def normalize_from(frm: Dict) -> str:
    try:
        addr = frm.get("emailAddress", {})
        name = addr.get("name") or ""
        email = addr.get("address") or ""
        return f"{name} <{email}>" if email else name
    except Exception:
        return ""


def build_row(
    msg: Dict,
    kept_links: List[str],
    attach_hits: List[Dict],
    lang_score: float,
    link_score: float,
    lang_hits: Dict[str, int],
) -> Dict:
    subject = msg.get("subject") or ""
    frm = normalize_from(msg.get("from") or {})
    rid = msg.get("id")
    rdt = msg.get("receivedDateTime")
    web = msg.get("webLink")
    strategy = msg.get("_matched_strategy", "")
    confidence = min(1.0, lang_score + link_score + (0.25 if attach_hits else 0.0))
    return {
        "id": rid,
        "subject": subject,
        "from": frm,
        "receivedDateTime": rdt,
        "hasAttachments": bool(msg.get("hasAttachments")),
        "matched_strategy": strategy,
        "match_confidence": round(confidence, 3),
        "lang_hits_he": lang_hits.get("hits_he", 0),
        "lang_hits_en": lang_hits.get("hits_en", 0),
        "matched_links": kept_links,
        "matched_attachments": attach_hits,
        "webLink": web,
    }


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
    p.add_argument("--lookback-days", type=int, default=DEFAULTS["lookback_days"])
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
    args = p.parse_args()

    # Auth
    gc = GraphClient(
        client_id=args.client_id,
        authority=f"https://login.microsoftonline.com/{args.authority}",
    )
    gc.login()

    # Client-side date threshold
    since_dt = iso_utc_now_minus_days(args.lookback_days)

    # Run all strategies (dedupe by id)
    seen: Dict[str, Dict] = {}
    for strat in STRATEGIES:
        print(f"Running strategy: {strat['name']}")
        msgs = run_strategy(
            gc,
            strategy=strat,
            page_size=args.page_size,
            max_pages=args.max_pages,
            select_fields=DEFAULTS["select_fields"],
        )
        for m in msgs:
            mid = m.get("id")
            if mid and mid not in seen:
                seen[mid] = m

    print(f"Candidates fetched: {len(seen)}")

    # Score + enrich + DATE FILTER (client-side)
    rows: List[Dict] = []
    for mid, msg in seen.items():
        # Skip if missing or unparsable date
        rdt_raw = msg.get("receivedDateTime")
        try:
            # Graph returns ISO 8601 with Z; make it aware
            rdt = dt.datetime.fromisoformat(rdt_raw.replace("Z", "+00:00"))
        except Exception:
            rdt = None

        if rdt is None or rdt < since_dt:
            continue

        body = msg.get("body") or {}
        body_text = body_as_text(body)
        urls = extract_urls_from_body(body)
        kept_links, link_score = score_links(urls)

        attach_hits: List[Dict] = []
        if msg.get("hasAttachments"):
            try:
                for a in fetch_attachments(gc, mid):
                    if prefers_attachment(a.get("name", ""), a.get("contentType", "")):
                        attach_hits.append(
                            {
                                "name": a.get("name"),
                                "contentType": a.get("contentType"),
                                "size": a.get("size"),
                                "odata_type": a.get("odata_type"),
                            }
                        )
            except Exception as e:
                attach_hits.append({"error": f"attachments_fetch_failed: {e}"})

        lang_score, lang_hits = language_confidence(
            subject=msg.get("subject") or "",
            preview=msg.get("bodyPreview") or "",
            body_text=body_text,
        )

        row = build_row(msg, kept_links, attach_hits, lang_score, link_score, lang_hits)
        if row["match_confidence"] >= args.min_confidence:
            rows.append(row)

    # Sort by date desc (client-side)
    rows.sort(key=lambda r: r["receivedDateTime"] or "", reverse=True)

    # Output paths
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = args.out_json or f"invoice_messages_{ts}.json"
    out_csv = args.out_csv or f"invoice_messages_{ts}.csv"

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
    print(f"\nSaved {len(rows)} matches")
    print(f"JSON: {os.path.abspath(out_json)}")
    print(f"CSV : {os.path.abspath(out_csv)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
