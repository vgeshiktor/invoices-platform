#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Find invoice/receipt emails in Outlook via Microsoft Graph (Device Code auth).
- Searches with multi-strategy ($search + $filter, Hebrew + English)
- Paginates
- Fetches attachments & message body
- Extracts links from HTML/text
- Scores match confidence (Heb/Eng keywords, attachments, link heuristics)
- Outputs CSV + JSON

Usage:
  python graph_invoice_finder.py \
    --client-id "<YOUR_CLIENT_ID>" \
    --out-json invoices.json \
    --out-csv invoices.csv

Optional:
  --authority "https://login.microsoftonline.com/common"
  --lookback-days 120
  --top 100
  --min-confidence 0.55
  --save-cache ".token_cache.bin"
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import msal
import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

DEFAULT_CONFIG = {
    "query_defaults": {
        "endpoint_base": f"{GRAPH_BASE}/me/messages",
        "headers": {"ConsistencyLevel": "eventual"},
        "params_common": {
            "$count": "true",
            "$select": "id,subject,from,receivedDateTime,hasAttachments,bodyPreview,webLink",
            "$orderby": "receivedDateTime desc",
        },
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
            "statement",
            "bill",
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
            "view bill",
            "download bill",
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
        "name_hints": ["invoice", "receipt", "חשבונית", "קבלה", "statement", "bill"],
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
            "view",
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
            "intuit.com",
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
                "bill",
                "statement",
                "view",
            ],
            "file_like_suffixes": [".pdf", ".html", ".htm", ".aspx"],
        },
    },
    "strategies": [
        {
            "name": "attachments_and_keywords_recent",
            "params": {
                "$filter": "(hasAttachments eq true) and (receivedDateTime ge {ISO_UTC_NOW_MINUS_LOOKBACK})",
                "$search": '"invoice OR receipt OR חשבונית OR קבלה"',
            },
        },
        {
            "name": "keywords_only_recent",
            "params": {
                "$filter": "receivedDateTime ge {ISO_UTC_NOW_MINUS_LOOKBACK}",
                "$search": '"(invoice OR receipt OR statement OR billing OR חשבונית OR קבלה OR תשלום)"',
            },
        },
        {
            "name": "hebrew_bias",
            "params": {
                "$filter": "receivedDateTime ge {ISO_UTC_NOW_MINUS_LOOKBACK}",
                "$search": '"(חשבונית OR \\"חשבונית מס\\" OR קבלה OR תשלום OR \\"חשבונית מס קבלה\\")"',
            },
        },
        {
            "name": "provider_whitelist_bump",
            "params": {
                "$filter": "receivedDateTime ge {ISO_UTC_NOW_MINUS_LOOKBACK}",
                "$search": '"(greeninvoice.co.il OR icount.co.il OR ezcount.co.il OR quickbooks.intuit.com OR stripe.com OR paypal.com OR zoho.com OR xero.com OR shopify.com OR tax.gov.il)"',
            },
        },
    ],
    "scoring": {
        "he_weight": 1.2,
        "en_weight": 1.0,
        "base_attachment_bonus": 0.25,
        "base_link_bonus": 0.25,
    },
}


def log(msg: str):
    print(msg, file=sys.stderr)


def acquire_token_device(
    client_id: str, authority: str, scope: str, cache_path: str | None
):
    cache = None
    if cache_path:
        cache = msal.SerializableTokenCache()
        if os.path.exists(cache_path):
            cache.deserialize(open(cache_path, "r", encoding="utf-8").read())

    app = msal.PublicClientApplication(
        client_id=client_id, authority=authority, token_cache=cache
    )

    # Try cached accounts first
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent([scope], account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=[scope])
        if "user_code" not in flow:
            raise RuntimeError(
                f"Device flow failed to initiate: {json.dumps(flow, indent=2)}"
            )
        print("== Device Code Authentication ==")
        print(flow["message"])  # Contains login URL and code
        result = app.acquire_token_by_device_flow(flow)

    if cache_path and cache and cache.has_state_changed:
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(cache.serialize())

    if "access_token" not in result:
        raise RuntimeError(f"Authentication failed: {result}")

    return result["access_token"]


def graph_get(session: requests.Session, url: str, params: dict):
    r = session.get(url, params=params)
    if r.status_code != 200:
        raise RuntimeError(f"Graph GET failed {r.status_code}: {r.text}")
    return r.json()


def paginate_messages(
    session: requests.Session, base_url: str, params: dict, max_pages: int = 50
):
    page = 0
    url = base_url
    while url and page < max_pages:
        data = graph_get(session, url, params if page == 0 else {})
        yield from data.get("value", [])
        url = data.get("@odata.nextLink")
        page += 1


def fetch_message_body(session: requests.Session, msg_id: str):
    url = f"{GRAPH_BASE}/me/messages/{msg_id}"
    params = {"$select": "id,body,bodyPreview,webLink,internetMessageId"}
    data = graph_get(session, url, params)
    body = data.get("body", {})
    return body.get("contentType", "text"), body.get("content", "") or ""


def fetch_attachments(session: requests.Session, msg_id: str):
    url = f"{GRAPH_BASE}/me/messages/{msg_id}/attachments"
    data = graph_get(session, url, params={})
    out = []
    for a in data.get("value", []):
        atype = a.get("@odata.type", "")
        # We keep FileAttachment & ItemAttachment meta (no file download here)
        if "fileAttachment" in atype.lower() or "itemAttachment" in atype.lower():
            out.append(
                {
                    "name": a.get("name"),
                    "contentType": a.get("contentType"),
                    "size": a.get("size"),
                    "isInline": a.get("isInline"),
                }
            )
    return out


URL_REGEX = re.compile(r"""(?i)\bhttps?://[^\s<>"'()]+""", re.UNICODE)


def extract_links_from_body(content_type: str, body: str):
    # Prefer robust parsing, but keep stdlib-only (regex). Works for text or HTML.
    urls = re.findall(URL_REGEX, body or "")
    return list(dict.fromkeys(urls))  # dedupe, keep order


def is_invoicey_link(url: str, cfg: dict) -> bool:
    try:
        p = urlparse(url)
        if not p.scheme or not p.netloc:
            return False
        if cfg["require_https"] and p.scheme.lower() != "https":
            return False
        host = p.netloc.lower()
        path = (p.path or "").lower()
        q = (p.query or "").lower()

        if any(dom in host for dom in cfg["trusted_providers"]):
            return True

        if any(k in url.lower() for k in cfg["url_keywords"]):
            return True

        if any(
            sfx for sfx in cfg["heuristics"]["file_like_suffixes"] if path.endswith(sfx)
        ):
            return True

        if any(seg in path for seg in cfg["heuristics"]["path_patterns"]):
            return True

        # occasionally query params carry signal
        if any(
            k in q
            for k in ["invoice", "receipt", "doc", "download", "statement", "bill"]
        ):
            return True

    except Exception:
        return False
    return False


def score_message(
    subject: str,
    body_preview: str,
    links: list[str],
    attachments: list[dict],
    cfg: dict,
    kws: dict,
):
    text = f"{subject or ''}\n{body_preview or ''}".lower()

    he_hits = sum(1 for k in kws["hebrew_core"] if k in text)
    en_hits = sum(1 for k in kws["english_core"] if k in text)
    ctx_hits = sum(
        1 for k in kws["hebrew_context"] + kws["english_context"] if k in text
    )

    he_w = cfg["he_weight"]
    en_w = cfg["en_weight"]
    base = (he_hits * he_w + en_hits * en_w) / (
        2.0 + ctx_hits * 0.15 if (he_hits + en_hits + ctx_hits) else 1.0
    )

    # Bonuses
    bonus = 0.0
    if attachments:
        # Check if any attachment name/extension looks relevant
        att_cfg = DEFAULT_CONFIG["attachment_detection"]
        good = False
        for a in attachments:
            name = (a.get("name") or "").lower()
            if any(h in name for h in att_cfg["name_hints"]):
                good = True
            _, ext = os.path.splitext(name)
            if ext.lower() in att_cfg["extensions_prefer"]:
                good = True
        if good:
            bonus += cfg["base_attachment_bonus"]

    if links:
        link_cfg = DEFAULT_CONFIG["link_detection"]
        if any(is_invoicey_link(u, link_cfg) for u in links):
            bonus += cfg["base_link_bonus"]

    score = min(1.0, base + bonus)
    return float(score), he_hits, en_hits, ctx_hits


def merge_unique_by_id(rows):
    seen = {}
    for r in rows:
        rid = r["id"]
        if rid not in seen or r["match_confidence"] > seen[rid]["match_confidence"]:
            seen[rid] = r
    return list(seen.values())


def main():
    ap = argparse.ArgumentParser(
        description="Find invoice/receipt emails via Microsoft Graph (Device Code)."
    )
    ap.add_argument(
        "--client-id",
        required=True,
        help="Azure App (Client) ID for a Public Client app with Mail.Read.",
    )
    ap.add_argument(
        "--authority",
        default="https://login.microsoftonline.com/consumers",
        help="Tenant or policy. Use 'common' or a specific tenant if needed.",
    )
    ap.add_argument(
        "--scope", default="Mail.Read", help="Graph permission scope to request."
    )
    ap.add_argument(
        "--lookback-days", type=int, default=120, help="How many days back to search."
    )
    ap.add_argument("--top", type=int, default=100, help="$top page size per request.")
    ap.add_argument(
        "--min-confidence",
        type=float,
        default=0.55,
        help="Minimum score to include in output.",
    )
    ap.add_argument("--out-json", default="invoices.json", help="Output JSON path.")
    ap.add_argument("--out-csv", default="invoices.csv", help="Output CSV path.")
    ap.add_argument(
        "--save-cache", default=".token_cache.bin", help="Token cache file (optional)."
    )
    args = ap.parse_args()

    token = acquire_token_device(
        client_id=args.client_id,
        authority=args.authority,
        scope=args.scope,
        cache_path=args.save_cache,
    )

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            # Required for $count with $search:
            "ConsistencyLevel": DEFAULT_CONFIG["query_defaults"]["headers"][
                "ConsistencyLevel"
            ],
        }
    )

    # Build common params
    since_dt = (
        datetime.now(timezone.utc) - timedelta(days=args.lookback_days)
    ).replace(microsecond=0)
    since_iso = since_dt.isoformat().replace("+00:00", "Z")
    params_common = dict(DEFAULT_CONFIG["query_defaults"]["params_common"])
    params_common["$top"] = str(args.top)

    strategies = DEFAULT_CONFIG["strategies"]
    all_rows = []

    for s in strategies:
        name = s["name"]
        params = dict(params_common)
        sf = s["params"]["$filter"].format(ISO_UTC_NOW_MINUS_LOOKBACK=since_iso)
        params["$filter"] = sf
        params["$search"] = s["params"]["$search"]

        log(f"Running strategy: {name}")
        for msg in paginate_messages(
            session, DEFAULT_CONFIG["query_defaults"]["endpoint_base"], params
        ):
            msg_id = msg.get("id")
            subject = msg.get("subject") or ""
            has_attachments = bool(msg.get("hasAttachments"))
            body_preview = msg.get("bodyPreview") or ""
            received = msg.get("receivedDateTime") or ""
            web_link = msg.get("webLink") or ""
            sender = (msg.get("from") or {}).get("emailAddress", {}).get("address", "")

            # Fetch body (for link extraction)
            ctype, body = fetch_message_body(session, msg_id)
            links = extract_links_from_body(ctype, body)

            # Attachments metadata (names/types/sizes)
            attachments = fetch_attachments(session, msg_id) if has_attachments else []

            score, he_hits, en_hits, ctx_hits = score_message(
                subject=subject,
                body_preview=body_preview,
                links=links,
                attachments=attachments,
                cfg=DEFAULT_CONFIG["scoring"],
                kws=DEFAULT_CONFIG["keyword_sets"],
            )

            if score >= args.min_confidence:
                # Keep only invoice-y links (filter)
                link_cfg = DEFAULT_CONFIG["link_detection"]
                good_links = [u for u in links if is_invoicey_link(u, link_cfg)]

                # Keep only relevant attachments by name/ext; still show others if none matched
                att_cfg = DEFAULT_CONFIG["attachment_detection"]
                matched_atts = []
                for a in attachments:
                    nm = (a.get("name") or "").lower()
                    _, ext = os.path.splitext(nm)
                    if (
                        any(h in nm for h in att_cfg["name_hints"])
                        or ext.lower() in att_cfg["extensions_prefer"]
                    ):
                        matched_atts.append(a)

                row = {
                    "id": msg_id,
                    "subject": subject,
                    "from.emailAddress.address": sender,
                    "receivedDateTime": received,
                    "hasAttachments": has_attachments,
                    "matched_strategy": name,
                    "match_confidence": round(score, 3),
                    "matched_keywords": {
                        "hebrew_hits": he_hits,
                        "english_hits": en_hits,
                        "context_hits": ctx_hits,
                    },
                    "matched_links": good_links,
                    "matched_attachments": matched_atts
                    if matched_atts
                    else attachments[:3],  # cap preview
                    "webLink": web_link,
                }
                all_rows.append(row)

    # Deduplicate keeping highest confidence per message
    final_rows = merge_unique_by_id(all_rows)

    # Save JSON
    with open(args.out_json, "w", encoding="utf-8") as jf:
        json.dump(final_rows, jf, ensure_ascii=False, indent=2)

    # Save CSV (flat)
    csv_cols = [
        "id",
        "subject",
        "from.emailAddress.address",
        "receivedDateTime",
        "hasAttachments",
        "matched_strategy",
        "match_confidence",
        "webLink",
        "links_count",
        "attachments_count",
        "hebrew_hits",
        "english_hits",
        "context_hits",
        "links_preview",
        "attachments_preview",
    ]
    with open(args.out_csv, "w", encoding="utf-8", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=csv_cols)
        writer.writeheader()
        for r in final_rows:
            writer.writerow(
                {
                    "id": r["id"],
                    "subject": r["subject"],
                    "from.emailAddress.address": r["from.emailAddress.address"],
                    "receivedDateTime": r["receivedDateTime"],
                    "hasAttachments": r["hasAttachments"],
                    "matched_strategy": r["matched_strategy"],
                    "match_confidence": r["match_confidence"],
                    "webLink": r["webLink"],
                    "links_count": len(r["matched_links"]),
                    "attachments_count": len(r["matched_attachments"]),
                    "hebrew_hits": r["matched_keywords"]["hebrew_hits"],
                    "english_hits": r["matched_keywords"]["english_hits"],
                    "context_hits": r["matched_keywords"]["context_hits"],
                    "links_preview": " | ".join(r["matched_links"][:3]),
                    "attachments_preview": " | ".join(
                        (a.get("name") or "") for a in r["matched_attachments"][:3]
                    ),
                }
            )

    print(f"Done. Wrote {len(final_rows)} matches to:")
    print(f"  JSON: {args.out_json}")
    print(f"  CSV : {args.out_csv}")


if __name__ == "__main__":
    main()
