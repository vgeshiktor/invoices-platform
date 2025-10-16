#!/usr/bin/env python3
"""
Graph Invoice Finder
--------------------
- Auth: Device Code (MSAL PublicClientApplication)
- Queries Microsoft Graph `me/messages` with $search (Heb/Eng keywords) + optional filters
- Paginates results
- Fetches attachments for candidates
- Extracts and scores links in message body
- Emits JSON and CSV

Usage:
  python graph_invoice_finder.py --client-id <APP_ID> [--lookback-days 120] [--page-size 100] [--max-pages 20] [--authority common]

Output:
  ./invoice_messages_<YYYYmmdd_HHMMSS>.json
  ./invoice_messages_<YYYYmmdd_HHMMSS>.csv
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
SCOPES = ["Mail.Read"]  # device-code friendly

# -------------------------------
# Config (mirrors the JSON you approved)
# -------------------------------
CONFIG = {
    "params_common": {
        "$count": "true",
        "$select": "id,subject,from,receivedDateTime,hasAttachments,body,bodyPreview,webLink",
        "$orderby": "receivedDateTime desc",
    },
    "keyword_sets": {
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
    },
    "attachment_detection": {
        "extensions_prefer": [
            ".pdf",
            ".tif",
            ".tiff",
            ".jpg",
            ".jpeg",
            ".png",
            ".xlsx",
            ".xls",
        ],
        "name_hints": ["invoice", "receipt", "חשבונית", "קבלה"],
    },
    "link_detection": {
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
    },
    "language_scoring": {
        "he_weight": 1.2,
        "en_weight": 1.0,
        "min_confidence_threshold": 0.55,
    },
    "graph_query_strategies": [
        {
            "name": "attachments_and_keywords_recent",
            "filter_tpl": "receivedDateTime ge {since}",
            "search": '"invoice OR receipt OR חשבונית OR קבלה"',
        },
        {
            "name": "keywords_only_recent",
            "filter_tpl": "receivedDateTime ge {since}",
            "search": '"(invoice OR receipt OR statement OR billing OR חשבונית OR קבלה OR תשלום)"',
        },
        {
            "name": "hebrew_bias",
            "filter_tpl": "receivedDateTime ge {since}",
            "search": r'"(חשבונית OR \"חשבונית מס\" OR קבלה OR תשלום OR \"חשבונית מס קבלה\")"',
        },
        {
            "name": "provider_whitelist_bump",
            "filter_tpl": "receivedDateTime ge {since}",
            "search": '"(greeninvoice.co.il OR icount.co.il OR ezcount.co.il OR quickbooks.intuit.com OR stripe.com OR paypal.com OR zoho.com OR xero.com OR shopify.com OR tax.gov.il)"',
        },
    ],
}

# -------------------------------
# Utilities
# -------------------------------


def iso_utc_now_minus_days(days: int) -> str:
    t = dt.datetime.utcnow() - dt.timedelta(days=days)
    return t.replace(microsecond=0).isoformat() + "Z"


def ensure_list(x):
    return x if isinstance(x, list) else [x]


URL_RE = re.compile(r'https?://[^\s<>"\'\]]+', re.IGNORECASE)


def extract_urls_from_body(body: Dict) -> List[str]:
    """Prefer HTML; fallback to text."""
    content_type = (body or {}).get("contentType", "")
    content = (body or {}).get("content", "") or ""
    txt = unescape(content)
    urls = []
    if content_type.lower() == "html":
        urls = URL_RE.findall(txt)
    else:
        urls = URL_RE.findall(txt)
    # de-dup, normalize
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
    """Return (kept_urls, score_contrib) based on provider & patterns."""
    ld = CONFIG["link_detection"]
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
        has_suf = any(
            u_l.endswith(s) or f"?{s}" in u_l for s in suffixes
        )  # light heuristic

        # keep if trusted OR looks like an invoice link by heuristics
        if trust or has_kw or has_pat or has_suf:
            kept.append(u)
            # scoring: trusted > suffix > keyword/pattern
            if trust:
                score += 0.3
            if has_suf:
                score += 0.2
            if has_kw or has_pat:
                score += 0.1

    return kept, min(score, 0.8)


def count_hits(text: str, needles: List[str]) -> int:
    t = text.lower()
    return sum(1 for n in needles if n.lower() in t)


def language_confidence(
    subject: str, preview: str, body_text: str
) -> Tuple[float, Dict[str, int]]:
    ks = CONFIG["keyword_sets"]
    he_core = ks["hebrew_core"] + ks["hebrew_context"]
    en_core = ks["english_core"] + ks["english_context"]
    blob = f"{subject}\n{preview}\n{body_text}".lower()
    hits_he = count_hits(blob, he_core)
    hits_en = count_hits(blob, en_core)

    weights = CONFIG["language_scoring"]
    score = (
        hits_he * weights["he_weight"] * 0.05 + hits_en * weights["en_weight"] * 0.05
    )
    score = min(score, 0.8)
    return score, {"hits_he": hits_he, "hits_en": hits_en}


def prefers_attachment(name: str, content_type: str) -> bool:
    ext_pref = CONFIG["attachment_detection"]["extensions_prefer"]
    hints = CONFIG["attachment_detection"]["name_hints"]
    n = (name or "").lower()
    ct = (content_type or "").lower()
    if any(n.endswith(ext) for ext in ext_pref):
        return True
    if any(h in n for h in hints):
        return True
    if "pdf" in ct:
        return True
    return False


# -------------------------------
# Graph client (requests + MSAL device code)
# -------------------------------


@dataclass
class GraphClient:
    client_id: str
    authority: str = "https://login.microsoftonline.com/common"
    _session: requests.Session = field(init=False, default_factory=requests.Session)
    _token: Optional[str] = field(init=False, default=None)

    def login(self):
        app = msal.PublicClientApplication(self.client_id, authority=self.authority)
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(
                "Failed to create device flow. Check client id / authority."
            )
        print("\n== Device Code ==")
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            raise RuntimeError(f"Auth failed: {result}")
        self._token = result["access_token"]

    @property
    def headers_base(self):
        if not self._token:
            raise RuntimeError("Not authenticated")
        return {"Authorization": f"Bearer {self._token}"}

    def get(self, url: str, params: Dict, use_search: bool = False) -> Dict:
        headers = dict(self.headers_base)
        if use_search:
            headers["ConsistencyLevel"] = "eventual"
        resp = self._session.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code >= 400:
            raise RuntimeError(f"GET {url} failed: {resp.status_code} {resp.text}")
        return resp.json()


# -------------------------------
# Core finder
# -------------------------------


def run_strategy(
    gc: GraphClient,
    name: str,
    filter_expr: str,
    search_expr: str,
    page_size: int,
    max_pages: int,
    params_common: Dict,
) -> List[Dict]:
    url = f"{GRAPH_BASE}/me/messages"
    params = dict(params_common)

    if search_expr:
        # Avoid InefficientFilter
        params.pop("$orderby", None)
        params.pop("$count", None)
        # Smaller pages are friendlier on search
        params["$top"] = str(min(page_size, 50))
        params["$top"] = 50
        params["$filter"] = filter_expr
        params["$search"] = search_expr

    out = []
    pages = 0
    next_url = url
    next_params = params

    while next_url and pages < max_pages:
        pages += 1
        data = gc.get(next_url, next_params, use_search=True)
        value = data.get("value", [])
        out.extend(value)
        next_url = data.get("@odata.nextLink")
        next_params = {}  # nextLink already contains params

    # tag with strategy
    for m in out:
        m["_matched_strategy"] = name
    return out


def fetch_attachments(gc: GraphClient, message_id: str) -> List[Dict]:
    url = f"{GRAPH_BASE}/me/messages/{message_id}/attachments"
    attachments = []
    while url:
        data = gc.get(url, params={}, use_search=False)
        value = data.get("value", [])
        for a in value:
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


def body_as_text(body: Dict) -> str:
    if not body:
        return ""
    ct = (body.get("contentType") or "").lower()
    c = body.get("content") or ""
    if ct == "html":
        # crude strip tags; we only need substring matches
        c = re.sub(r"<script.*?>.*?</script>", " ", c, flags=re.I | re.S)
        c = re.sub(r"<style.*?>.*?</style>", " ", c, flags=re.I | re.S)
        c = re.sub(r"<[^>]+>", " ", c)
    return unescape(c)


def build_result_row(
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

    # final blended confidence
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--client-id", required=True, help="Entra App (public client) Application ID"
    )
    ap.add_argument(
        "--authority",
        default="common",
        help="Tenant: common | consumers | organizations | <tenant-id>",
    )
    ap.add_argument("--lookback-days", type=int, default=120)
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument(
        "--min-confidence",
        type=float,
        default=CONFIG["language_scoring"]["min_confidence_threshold"],
    )
    args = ap.parse_args()

    authority_url = f"https://login.microsoftonline.com/{args.authority}"
    gc = GraphClient(client_id=args.client_id, authority=authority_url)
    gc.login()

    since_iso = iso_utc_now_minus_days(args.lookback_days)

    all_msgs_by_id: Dict[str, Dict] = {}
    for strat in CONFIG["graph_query_strategies"]:
        name = strat["name"]
        f_expr = strat["filter_tpl"].format(since=since_iso)
        s_expr = strat["search"]
        print(f"Running strategy: {name}")
        msgs = run_strategy(
            gc,
            name=name,
            filter_expr=f_expr,
            search_expr=s_expr,
            page_size=args.page_size,
            max_pages=args.max_pages,
            params_common=CONFIG["params_common"],
        )
        for m in msgs:
            mid = m.get("id")
            # de-dup by keeping the most recent seen (they're identical anyway)
            if mid and mid not in all_msgs_by_id:
                all_msgs_by_id[mid] = m

    print(f"Candidates: {len(all_msgs_by_id)}")

    rows = []
    for mid, msg in all_msgs_by_id.items():
        body = msg.get("body") or {}
        body_text = body_as_text(body)
        urls = extract_urls_from_body(body)
        kept_links, link_score = score_links(urls)

        # attachments if indicated
        attach_hits = []
        if msg.get("hasAttachments"):
            try:
                atts = fetch_attachments(gc, mid)
                for a in atts:
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
                # Don't break the run on attachment errors
                attach_hits.append({"error": f"attachments_fetch_failed: {e}"})

        # language confidence based on Heb/Eng keywords
        lang_score, lang_hits = language_confidence(
            subject=msg.get("subject") or "",
            preview=msg.get("bodyPreview") or "",
            body_text=body_text,
        )

        row = build_result_row(
            msg, kept_links, attach_hits, lang_score, link_score, lang_hits
        )
        if row["match_confidence"] >= args.min_confidence:
            rows.append(row)

    # Sort by receivedDateTime desc
    rows.sort(key=lambda r: r["receivedDateTime"] or "", reverse=True)

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = f"invoice_messages_{ts}.json"
    csv_path = f"invoice_messages_{ts}.csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    # Flatten for CSV
    def join_list(x):
        if isinstance(x, list):
            return "; ".join(
                json.dumps(i, ensure_ascii=False) if isinstance(i, dict) else str(i)
                for i in x
            )
        return x

    flat = []
    for r in rows:
        flat.append(
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
                "matched_links": join_list(r["matched_links"]),
                "matched_attachments": join_list(r["matched_attachments"]),
                "webLink": r["webLink"],
            }
        )
    pd.DataFrame(flat).to_csv(csv_path, index=False)

    print(f"\nSaved {len(rows)} matches")
    print(f"JSON: {os.path.abspath(json_path)}")
    print(f"CSV : {os.path.abspath(csv_path)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
