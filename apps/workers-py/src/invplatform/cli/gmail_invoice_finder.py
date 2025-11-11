#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gmail_invoice_finder.v1.0.py
============================

סקריפט להורדת חשבוניות/קבלות מחשבון Gmail, בהשראת הזרימה של graph_invoice_finder:
- חיפוש הודעות עם צרופות/לינקים רלוונטיים בין תאריכים
- הורדת PDF מצורף
- לינקים: הורדה ישירה של PDF, ובזק (myinvoice.bezeq.co.il) דרך Playwright ע"י ניתוח בקשת API (GetAttachedInvoiceById)
- אימות רלוונטיות PDF עם PyMuPDF (מילות מפתח חיוביות/שליליות)
- מניעת דריסה ו־hash de-dup
- דוחות JSON/CSV + Download report
- אפשרות להחריג תיקיית Sent
- דגלי ניטור (--save-candidates/--save-nonmatches/--explain) כמו ב-graph_invoice_finder

תלויות:
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    pip install requests beautifulsoup4 lxml pymupdf playwright
    playwright install chromium

הכנת OAuth ל-Gmail:
1) צור פרויקט ב-Google Cloud → הפעל Gmail API → צור OAuth Client ID (Desktop App)
2) הורד את credentials.json ושמור לצד הסקריפט
3) בהרצה הראשונה יווצר token.json לאחר אישור בדפדפן

דוגמאות הרצה:
--------------
# בסיסי: טווח תאריכים, שמירה לתיקיית invoices_out
python -m invplatform.cli.gmail_invoice_finder \
  --start-date 2025-09-01 --end-date 2025-10-01 \
  --invoices-dir invoices_out \
  --verify \
  --save-json invoices_gmail.json \
  --save-csv  invoices_gmail.csv \
  --download-report download_report_gmail.json

# החרגת 'נשלח', הרצה ו־trace עבור בזק:
python -m invplatform.cli.gmail_invoice_finder \
  --start-date 2025-09-01 --end-date 2025-10-01 \
  --invoices-dir invoices_out \
  --exclude-sent \
  --verify --debug \
  --bezeq-headful --bezeq-trace --bezeq-screenshots

# חיפוש מותאם ידנית (יגבר על בניית השאילתה האוטומטית):
python -m invplatform.cli.gmail_invoice_finder \
  --gmail-query 'in:anywhere -in:sent -from:me after:2025/09/01 before:2025/10/01 (filename:pdf OR "חשבונית" OR invoice)' \
  --invoices-dir invoices_out --verify

הערות:
- תאריך Gmail בשאילתא בפורמט YYYY/MM/DD (עם /), לא מקפים.
- ברירת מחדל הסקריפט בונה שאילתה טובה לרוב, כולל החרגת 'נשלח' אם ביקשת.
- הסקריפט מייצר quarantine/ לפריטים לא וודאיים אם ביקשת --verify ו/או לא עמדו בסף.
"""

import argparse
import base64
import csv
import datetime as dt
import hashlib
import json
import logging
import os
import re
import sys
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, unquote, urlparse

# ==== Google / Gmail API ====
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GReq
from googleapiclient.discovery import build

import requests
from bs4 import BeautifulSoup

# Playwright (לבזק)
from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

from ..domain import constants as domain_constants
from ..domain import files as domain_files
from ..domain import pdf as domain_pdf
from ..domain import relevance as domain_relevance

DEFAULT_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


# --------------------------- Utilities ---------------------------
ensure_dir = domain_files.ensure_dir
sanitize_filename = domain_files.sanitize_filename
short_id_tag = domain_files.short_msg_tag
ensure_unique_path = domain_files.ensure_unique_path
sha256_bytes = domain_files.sha256_bytes
within_domain = domain_relevance.within_domain


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def now_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")


# --------------------------- Keywords & heuristics ---------------------------
EN_POS = domain_constants.EN_POS
HEB_POS = domain_constants.HEB_POS
EN_NEG = domain_constants.EN_NEG
HEB_NEG = domain_constants.HEB_NEG
TRUSTED_PROVIDERS = domain_constants.TRUSTED_PROVIDERS
is_municipal_text = domain_relevance.is_municipal_text
body_has_negative = domain_relevance.body_has_negative
body_has_positive = domain_relevance.body_has_positive

YES_DOMAINS = ["yes.co.il", "www.yes.co.il", "svc.yes.co.il"]


# --------------------------- PDF verification ---------------------------
pdf_keyword_stats = domain_pdf.pdf_keyword_stats
pdf_confidence = domain_pdf.pdf_confidence


def decide_pdf_relevance(path: str, trusted_hint: bool = False) -> Tuple[bool, Dict]:
    stats = pdf_keyword_stats(path)
    ok = stats["pos_hits"] >= 1 and stats["neg_hits"] == 0
    if trusted_hint and stats["neg_hits"] == 0 and stats["pos_hits"] == 0:
        ok = True
    return ok, stats


# --------------------------- Gmail client ---------------------------
class GmailClient:  # pragma: no cover - requires live Google OAuth
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        self.creds = None
        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(GReq())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                self.creds = flow.run_local_server(
                    host="localhost",
                    port=8080,
                    access_type="offline",
                    prompt="consent",
                    include_granted_scopes="true",
                )

            with open(token_path, "w") as token:
                token.write(self.creds.to_json())
        self.svc = build("gmail", "v1", credentials=self.creds, cache_discovery=False)

    def list_messages(self, q: str, max_results: int = 500, include_spam_trash: bool = False):
        user = "me"
        page_token = None
        fetched = 0
        while True:
            res = (
                self.svc.users()
                .messages()
                .list(
                    userId=user,
                    q=q,
                    maxResults=min(500, max(1, max_results - fetched)),
                    includeSpamTrash=include_spam_trash,
                    pageToken=page_token,
                )
                .execute()
            )
            for m in res.get("messages", []):
                yield m["id"]
                fetched += 1
                if fetched >= max_results:
                    return
            page_token = res.get("nextPageToken")
            if not page_token:
                break

    def get_message(self, msg_id: str) -> Dict:
        return self.svc.users().messages().get(userId="me", id=msg_id, format="full").execute()

    def get_attachment(self, msg_id: str, att_id: str) -> bytes:
        res = (
            self.svc.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=msg_id, id=att_id)
            .execute()
        )
        data = res.get("data", "")
        return base64.urlsafe_b64decode(data.encode("utf-8")) if data else b""


# --------------------------- Gmail helpers ---------------------------
def gmail_date(d: str) -> str:
    # Gmail search uses YYYY/MM/DD
    return d.replace("-", "/")


def build_gmail_query(start_date: str, end_date: str, exclude_sent: bool = True) -> str:
    # בסיס: טווח תאריכים
    parts = [f"after:{gmail_date(start_date)}", f"before:{gmail_date(end_date)}"]
    # לא לכלול נשלח / ממני
    if exclude_sent:
        parts += ["-in:sent", "-from:me"]

    # נרצה רק הודעות עם פוטנציאל חשבוניות: צרופות PDF או מילות מפתח (כולל הטיות עם ה' הידיעה)
    def quote_term(term: str) -> str:
        return f'"{term}"' if any(ch.isspace() for ch in term) else term

    def subject_term(term: str) -> str:
        inner = quote_term(term)
        return f"subject:{inner}"

    heb_terms: List[str] = []
    for term in HEB_POS:
        heb_terms.append(term)
        if term and not term.startswith("ה"):
            heb_terms.append(f"ה{term}")

    keyword_terms: List[str] = ["filename:pdf"]
    for term in heb_terms + EN_POS:
        keyword_terms.append(subject_term(term))
        keyword_terms.append(quote_term(term))

    # הסר כפילויות ושמור על סדר
    keyword_terms = list(dict.fromkeys(keyword_terms))
    keyword_expr = "(" + " OR ".join(keyword_terms) + ")"
    parts.append(keyword_expr)
    # אפשר לא להגביל ל-in:inbox כדי לתפוס ארכיון וכו’:
    parts.append("in:anywhere")
    return " ".join(parts)


def parse_headers(payload: dict) -> Dict[str, str]:
    h = {}
    for it in payload.get("headers") or []:
        name = it.get("name") or ""
        val = it.get("value") or ""
        h[name.lower()] = val
    return h


def extract_parts(payload: dict) -> List[dict]:
    # שטוח כל ה-MIME parts
    res = []

    def walk(p):
        if not p:
            return
        res.append(p)
        for c in p.get("parts") or []:
            walk(c)

    walk(payload)
    return res


def get_body_text(payload: dict) -> Tuple[str, str]:
    # מחזיר (html, plain)
    html, plain = "", ""
    for p in extract_parts(payload):
        mime = (p.get("mimeType") or "").lower()
        body = p.get("body") or {}
        data = body.get("data")
        if not data:
            continue
        try:
            raw = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
        except Exception:
            continue
        if mime == "text/html":
            html += raw + "\n"
        elif mime == "text/plain":
            plain += raw + "\n"
    return html, plain


def extract_links_from_html(html: str) -> List[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    links = [a["href"] for a in soup.find_all("a", href=True)]
    # גם מ-img map וכד’
    for tag in soup.find_all(["area"]):
        href = tag.get("href")
        if href:
            links.append(href)
    # ייחודיות
    return list(dict.fromkeys(links))


def extract_links_from_text(text: str) -> List[str]:
    urls = re.findall(r'https?://[^\s<>"\)\]]+', text or "", flags=re.I)
    return list(dict.fromkeys(urls))


def normalize_link(u: str) -> str:
    if not u:
        return u
    try:
        parsed = urlparse(u)
    except Exception:
        return u
    host = (parsed.hostname or "").lower()
    if host in {"www.google.com", "google.com"} and parsed.path.startswith("/url"):
        qs = parse_qs(parsed.query)
        for key in ("url", "q"):
            target = qs.get(key)
            if target:
                return unquote(target[0])
    return u


def _decode_data_url(data_url: str) -> Optional[bytes]:
    m = re.match(r"data:([^;]+);base64,(.+)", data_url, flags=re.I)
    if not m:
        return None
    try:
        blob = base64.b64decode(m.group(2))
    except Exception:
        return None
    return blob or None


def sha256_file(path: str) -> Optional[str]:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def load_existing_hash_index(inv_dir: str) -> Dict[str, str]:
    index: Dict[str, str] = {}
    if not os.path.isdir(inv_dir):
        return index
    for root, dirs, files in os.walk(inv_dir):
        dirs[:] = [d for d in dirs if d not in {"_tmp", "quarantine"}]
        for name in files:
            if not name.lower().endswith(".pdf"):
                continue
            path = os.path.join(root, name)
            digest = sha256_file(path)
            if digest and digest not in index:
                index[digest] = path
    return index


# --------------------------- Direct PDF via requests ---------------------------
def download_direct_pdf(
    url: str, referer: Optional[str] = None, ua: Optional[str] = None, verbose: bool = False
) -> Optional[Tuple[str, bytes]]:
    ua = ua or DEFAULT_BROWSER_UA

    def base_headers(include_referer: bool) -> Dict[str, str]:
        hdrs: Dict[str, str] = {
            "User-Agent": ua,
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "close",
            "Upgrade-Insecure-Requests": "1",
        }
        if include_referer and referer:
            hdrs["Referer"] = referer
        host = (urlparse(url).hostname or "").lower()
        if host.endswith("yes.co.il"):
            hdrs.setdefault("Origin", "https://www.yes.co.il")
            hdrs.setdefault("Sec-Fetch-Site", "cross-site")
            hdrs.setdefault("Sec-Fetch-Mode", "navigate")
            hdrs.setdefault("Sec-Fetch-Dest", "document")
            hdrs.setdefault("Sec-Fetch-User", "?1")
            hdrs.setdefault(
                "sec-ch-ua",
                '"Not/A)Brand";v="8", "Chromium";v="127", "Google Chrome";v="127"',
            )
            hdrs.setdefault("sec-ch-ua-platform", '"macOS"')
            hdrs.setdefault("sec-ch-ua-mobile", "?0")
        return hdrs

    attempts = [True] if referer else []
    attempts.append(False)

    for include_ref in attempts:
        try:
            hdrs = base_headers(include_ref)
            r = requests.get(url, headers=hdrs, timeout=30)
            if verbose:
                print(
                    f"[direct_pdf] {url} ref={'yes' if include_ref and referer else 'no'} -> status={r.status_code} ct={r.headers.get('Content-Type')} size={len(r.content)}"
                )
            ct = (r.headers.get("Content-Type") or "").lower()
            body = r.content
            if r.status_code == 403 and include_ref:
                # נסה שוב בלי referer
                continue
            if r.status_code == 200 and (
                "pdf" in ct or url.lower().endswith(".pdf") or body[:4] == b"%PDF"
            ):
                name = "link_invoice.pdf"
                cd = r.headers.get("Content-Disposition") or ""
                m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, flags=re.I)
                if m:
                    name = sanitize_filename(m.group(1))
                    if not name.lower().endswith(".pdf"):
                        name += ".pdf"
                return name, body
        except Exception as e:
            if verbose:
                print(f"[direct_pdf] {url} error: {e}")
            continue
    return None


def yes_fetch_with_browser(  # pragma: no cover - requires real Playwright/browser
    url: str, headless: bool, verbose: bool = False
) -> Dict[str, object]:
    """Attempt to render YES invoice HTML and capture embedded PDF bytes."""
    res: Dict[str, object] = {"ok": False, "notes": []}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=headless, args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                locale="he-IL",
                user_agent=DEFAULT_BROWSER_UA,
                extra_http_headers={"Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7"},
            )

            pdf_blob: Optional[bytes] = None
            pdf_name: Optional[str] = None

            def handle_response(resp):
                nonlocal pdf_blob, pdf_name
                if pdf_blob is not None:
                    return
                ct = (resp.headers.get("content-type") or "").lower()
                if "pdf" not in ct:
                    return
                try:
                    body = resp.body()
                except Exception as e:  # pragma: no cover
                    res["notes"].append(f"resp_body_err:{e}")
                    return
                if body[:4] == b"%PDF":
                    pdf_blob = body
                    cd = resp.headers.get("content-disposition") or ""
                    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, flags=re.I)
                    if m:
                        pdf_name = sanitize_filename(m.group(1))
                    else:
                        pdf_name = sanitize_filename(
                            os.path.basename(urlparse(resp.url).path) or ""
                        )

            context.on("response", handle_response)
            page = context.new_page()
            try:
                if verbose:
                    print(f"[yes_browser] navigate {url}")
                page.goto(url, wait_until="networkidle")
                try:
                    page.wait_for_function(
                        "() => { const el = document.querySelector('embed,iframe,object');"
                        " return el && el.src && el.src !== 'about:blank'; }",
                        timeout=5000,
                    )
                except PWTimeout:
                    pass

                if pdf_blob is None:
                    locator = page.locator("embed, iframe, object")
                    count = locator.count()
                    for idx in range(count):
                        handle = locator.nth(idx)
                        src = (handle.get_attribute("src") or "").strip()
                        if not src or src == "about:blank":
                            continue
                        candidate_name = handle.get_attribute("name") or ""
                        blob: Optional[bytes] = None
                        if src.startswith("data:"):
                            blob = _decode_data_url(src)
                        elif src.startswith("blob:"):
                            try:
                                arr = page.evaluate(
                                    """async (blobUrl) => {
                                        const resp = await fetch(blobUrl);
                                        const buf = await resp.arrayBuffer();
                                        return Array.from(new Uint8Array(buf));
                                    }""",
                                    src,
                                )
                                if arr:
                                    blob = bytes(arr)
                            except Exception as e:  # pragma: no cover
                                res["notes"].append(f"blob_fetch_err:{e}")
                        else:
                            try:
                                resp = context.request.get(src)
                                data = resp.body()
                                if data[:4] == b"%PDF":
                                    blob = data
                                    cd = resp.headers.get("content-disposition") or ""
                                    m = re.search(
                                        r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, flags=re.I
                                    )
                                    if m:
                                        candidate_name = m.group(1)
                            except Exception as e:  # pragma: no cover
                                res["notes"].append(f"http_fetch_err:{e}")
                        if blob:
                            pdf_blob = blob
                            pdf_name = sanitize_filename(candidate_name or os.path.basename(src))
                            break

                if pdf_blob:
                    res.update(
                        {"ok": True, "name": pdf_name or "yes_invoice.pdf", "blob": pdf_blob}
                    )
                else:
                    res["notes"].append("pdf_not_found")
            except Exception as e:  # pragma: no cover - Playwright runtime
                res["notes"].append(f"browser_err:{e}")
            finally:
                context.close()
                browser.close()
    except Exception as e:  # pragma: no cover - Playwright runtime
        res["notes"].append(f"browser_init_err:{e}")
    return res


# --------------------------- Bezeq (Playwright) ---------------------------
def normalize_myinvoice_url(u: str) -> str:
    s = (u or "").strip()
    s = s.replace("\\?", "?").replace("\\&", "&").replace("\\=", "=")
    s = s.replace("://myinvoice.bezeq.co.il//?", "://myinvoice.bezeq.co.il/?")
    s = re.sub(r"(://myinvoice\.bezeq\.co\.il)/+(?=\?)", r"\1/", s)
    return s


def bezeq_fetch_with_api_sniff(  # pragma: no cover - Playwright/network heavy
    url: str,
    out_dir: str,
    headless: bool,
    keep_trace: bool,
    take_screens: bool,
    verbose: bool,
) -> Dict:
    res = {"ok": False, "path": None, "notes": [], "normalized_url": None}

    def note(x: str):
        if verbose:
            print(x)
        res["notes"].append(x)

    normalized_url = normalize_myinvoice_url(url)
    res["normalized_url"] = normalized_url

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless, args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            accept_downloads=True,
            locale="he-IL",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            ),
            extra_http_headers={"Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7"},
        )
        if keep_trace:
            context.tracing.start(screenshots=True, snapshots=True, sources=False)

        api_urls: List[str] = []

        def on_console(m):
            try:
                t = m.type() if callable(getattr(m, "type", None)) else str(getattr(m, "type", ""))
                x = m.text() if callable(getattr(m, "text", None)) else str(getattr(m, "text", ""))
                note(f"console:{t}:{x}")
                if "GetAttachedInvoiceById" in x:
                    mm = re.search(r"https?://[^\s\"']+GetAttachedInvoiceById[^\s\"']+", x)
                    if mm:
                        api_urls.append(mm.group(0))
            except Exception:
                pass

        def on_request(req):
            try:
                if "GetAttachedInvoiceById" in (req.url or ""):
                    api_urls.append(req.url)
            except Exception:
                pass

        def on_response(resp):
            try:
                if "GetAttachedInvoiceById" in (resp.url or ""):
                    api_urls.append(resp.url)
            except Exception:
                pass

        page = context.new_page()
        page.on("console", on_console)
        context.on("request", on_request)
        context.on("response", on_response)

        page.goto(normalized_url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except PWTimeout:
            note("networkidle_timeout")

        def direct_api(u: str) -> Optional[Tuple[str, bytes]]:
            try:
                resp = context.request.get(u, headers={"Referer": normalized_url})
                body = resp.body()
                ct = (resp.headers.get("content-type") or "").lower()
                if (ct and "pdf" in ct) or body[:4] == b"%PDF":
                    name = "bezeq_invoice_api.pdf"
                    q = parse_qs(urlparse(u).query)
                    inv_id = (q.get("InvoiceId") or [""])[0]
                    cd = resp.headers.get("content-disposition") or ""
                    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, flags=re.I)
                    if m:
                        name = sanitize_filename(m.group(1))
                        if not name.lower().endswith(".pdf"):
                            name += ".pdf"
                    if inv_id:
                        stem, ext = os.path.splitext(name)
                        name = f"{stem}__{inv_id}{ext or '.pdf'}"
                    return name, body
            except Exception as e:
                note(f"direct_api_err:{e}")
            return None

        for u in list(dict.fromkeys(api_urls)):
            r = direct_api(u)
            if r:
                name, blob = r
                res["ok"] = True
                res["path"] = (name, blob)
                break

        if not res["ok"]:
            try:
                for sel in [
                    'text="להורדה"',
                    "text=להורדה",
                    'text="לצפייה"',
                    "text=לצפייה",
                    '[aria-label*="הורדה"]',
                    '[title*="הורדה"]',
                ]:
                    try:
                        page.locator(sel).first.click(timeout=2000)
                        time.sleep(1.0)
                        break
                    except Exception:
                        continue
            except Exception:
                pass
            for u in list(dict.fromkeys(api_urls)):
                r = direct_api(u)
                if r:
                    name, blob = r
                    res["ok"] = True
                    res["path"] = (name, blob)
                    break

        if keep_trace:
            try:
                context.tracing.stop(path=os.path.join(out_dir, f"bezeq_trace_{now_stamp()}.zip"))
            except Exception:
                pass
        context.close()
        browser.close()

    return res


# --------------------------- Flow helpers ---------------------------
def links_from_message(html: str, plain: str) -> List[str]:
    links = extract_links_from_html(html) + extract_links_from_text(plain)
    normalized: List[str] = []
    for u in links:
        if not u.startswith("http"):
            continue
        nu = normalize_link(u)
        if nu and nu.startswith("http"):
            normalized.append(nu)
    # ייחודיות
    return list(dict.fromkeys(normalized))


def should_consider_message(subject: str, preview: str) -> bool:
    t = f"{subject or ''} {preview or ''}"
    if body_has_negative(t):
        return False
    return body_has_positive(t) or is_municipal_text(t)


# --------------------------- Main ---------------------------
def main():  # pragma: no cover - CLI orchestration
    ap = argparse.ArgumentParser(description="Gmail Invoice Finder v1.0")
    ap.add_argument("--credentials", default="credentials.json")
    ap.add_argument("--token", default="token.json")

    ap.add_argument("--gmail-query", default=None, help="שאילתת Gmail מותאמת (עוקף בנייה אוטומטית)")
    ap.add_argument("--start-date", required=False, help="YYYY-MM-DD (לשילוב בשאילתא הנבנית)")
    ap.add_argument("--end-date", required=False, help="YYYY-MM-DD (לשילוב בשאילתא הנבנית)")
    ap.add_argument("--exclude-sent", action="store_true", help="החרגת נשלח/ממני בשאילתת Gmail")

    ap.add_argument("--invoices-dir", default="./invoices_out")
    ap.add_argument("--keep-quarantine", action="store_true")
    ap.add_argument("--download-report", default="download_report_gmail.json")
    ap.add_argument("--save-json", default=None)
    ap.add_argument("--save-csv", default=None)
    ap.add_argument("--save-candidates", default=None, help="Dump all raw PDF candidates to JSON")
    ap.add_argument(
        "--save-nonmatches", default=None, help="Dump rejected message metadata to JSON"
    )
    ap.add_argument("--max-messages", type=int, default=1000)

    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--explain", action="store_true")

    # Playwright / Bezeq
    ap.add_argument(
        "--bezeq-headful",
        action="store_true",
        help="פתח חלון Playwright (בזק/YES) במקום ריצה headless",
    )
    ap.add_argument("--bezeq-trace", action="store_true")
    ap.add_argument("--bezeq-screenshots", action="store_true")  # לא בשימוש ישיר כאן, דגל עתידי
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(message)s")

    inv_dir = ensure_dir(args.invoices_dir)
    quarant_dir = ensure_dir(os.path.join(inv_dir, "quarantine")) if args.keep_quarantine else None
    tmp_dir = ensure_dir(os.path.join(inv_dir, "_tmp"))

    # בניית שאילתא
    if args.gmail_query:
        query = args.gmail_query
    else:
        if not (args.start_date and args.end_date):
            print("כשלא מספקים --gmail-query חובה לתת --start-date ו--end-date לבניית השאילתא.")
            sys.exit(2)
        query = build_gmail_query(args.start_date, args.end_date, exclude_sent=args.exclude_sent)

    logging.info(f"Gmail query: {query}")

    gc = GmailClient(credentials_path=args.credentials, token_path=args.token)

    saved_rows: List[Dict] = []
    rejected_rows: List[Dict] = []
    download_report: List[Dict] = []
    candidate_entries: List[Dict] = []
    seen_hashes: Set[str] = set()
    hash_to_saved_path: Dict[str, str] = {}

    existing_index = load_existing_hash_index(inv_dir)
    if existing_index:
        seen_hashes.update(existing_index.keys())
        hash_to_saved_path.update(existing_index)

    def record_candidate(entry: Dict) -> None:
        if args.save_candidates:
            candidate_entries.append(entry)
        if args.explain:
            label = entry.get("name") or entry.get("url") or entry.get("type")
            decision = entry.get("decision") or ""
            reason = entry.get("reason") or ""
            confidence = entry.get("confidence")
            parts = [decision]
            if reason:
                parts.append(reason)
            if confidence is not None:
                parts.append(f"conf={confidence:.2f}")
            summary = ", ".join(p for p in parts if p)
            logging.info(
                "    candidate[%s] %s => %s", entry.get("type"), label, summary or "recorded"
            )

    def record_nonmatch(entry: Dict) -> None:
        rejected_rows.append(entry)
        if args.explain:
            subj = entry.get("subject") or entry.get("id")
            logging.info("    nonmatch[%s]: %s", subj, entry.get("reason"))

    idx = 0
    for msg_id in gc.list_messages(query, max_results=args.max_messages):
        idx += 1
        try:
            msg = gc.get_message(msg_id)
        except Exception as e:
            record_nonmatch({"id": msg_id, "reason": f"get_message_fail:{e}"})
            continue

        payload = msg.get("payload") or {}
        headers = parse_headers(payload)
        subject = headers.get("subject", "")
        from_addr = headers.get("from", "")
        internal_ts = int(msg.get("internalDate", "0")) // 1000
        received = dt.datetime.utcfromtimestamp(internal_ts).isoformat() if internal_ts else ""
        snippet = msg.get("snippet") or ""

        logging.info(f"[{idx}] {subject} | {from_addr} | {received}")

        # מסנן גבוה: תעדף רק הודעות עם ערך פוטנציאלי
        if not should_consider_message(subject, snippet):
            # אם יש PDF מצורף, עדיין נשקול – נמשיך לבדוק attach
            pass

        msg_tag = short_id_tag(msg_id)
        any_saved = False
        message_rejected = False

        # ---- Attachments ----
        parts = extract_parts(payload)
        for p in parts:
            mime = (p.get("mimeType") or "").lower()
            body = p.get("body") or {}
            filename = p.get("filename") or ""
            att_id = body.get("attachmentId")
            if not att_id:
                continue
            if "pdf" not in mime and not filename.lower().endswith(".pdf"):
                continue
            candidate = {
                "msg_id": msg_id,
                "type": "attachment",
                "name": filename,
                "mimeType": mime,
                "subject": subject,
                "from": from_addr,
                "receivedDateTime": received,
            }
            try:
                blob = gc.get_attachment(msg_id, att_id)
                if not blob:
                    continue
                h = sha256_bytes(blob)
                candidate["sha256"] = h
                if h in seen_hashes:
                    dup_path = hash_to_saved_path.get(h)
                    download_report.append(
                        {
                            "msg_id": msg_id,
                            "type": "attachment",
                            "name": filename,
                            "skip": "duplicate_hash",
                            **({"duplicate_of": dup_path} if dup_path else {}),
                        }
                    )
                    candidate.update(
                        {
                            "decision": "skip",
                            "reason": "duplicate_hash",
                            **({"duplicate_of": dup_path} if dup_path else {}),
                        }
                    )
                    record_candidate(candidate)
                    continue

                tmp_path = os.path.join(tmp_dir, f"tmp__{msg_tag}.pdf")
                with open(tmp_path, "wb") as f:
                    f.write(blob)

                trusted_hint = False
                if args.verify:
                    ok, stats = decide_pdf_relevance(tmp_path, trusted_hint=trusted_hint)
                else:
                    ok, stats = True, {"pos_hits": 1, "neg_hits": 0}
                confidence = pdf_confidence(stats)
                candidate.update(
                    {"stats": stats, "confidence": confidence, "trusted_hint": trusted_hint}
                )

                if not ok:
                    if quarant_dir:
                        out_q = ensure_unique_path(quarant_dir, filename or "file.pdf", tag=msg_tag)
                        os.replace(tmp_path, out_q)
                        download_report.append(
                            {
                                "msg_id": msg_id,
                                "type": "attachment",
                                "name": filename,
                                "path": out_q,
                                "ok": False,
                                "stats": stats,
                                "confidence": confidence,
                            }
                        )
                        candidate.update(
                            {"decision": "quarantine", "reason": "verify_failed", "path": out_q}
                        )
                    else:
                        os.remove(tmp_path)
                        download_report.append(
                            {
                                "msg_id": msg_id,
                                "type": "attachment",
                                "name": filename,
                                "reject": "verify_failed",
                                "stats": stats,
                                "confidence": confidence,
                            }
                        )
                        candidate.update({"decision": "reject", "reason": "verify_failed"})
                    record_candidate(candidate)
                    continue

                out_path = ensure_unique_path(inv_dir, filename or "invoice.pdf", tag=msg_tag)
                os.replace(tmp_path, out_path)
                seen_hashes.add(h)
                hash_to_saved_path[h] = out_path
                download_report.append(
                    {
                        "msg_id": msg_id,
                        "type": "attachment",
                        "name": filename,
                        "path": out_path,
                        "ok": True,
                        "stats": stats,
                        "confidence": confidence,
                    }
                )
                candidate.update({"decision": "saved", "path": out_path})
                record_candidate(candidate)
                saved_rows.append(
                    {
                        "id": msg_id,
                        "subject": subject,
                        "from": from_addr,
                        "receivedDateTime": received,
                        "source": "attachment",
                        "path": out_path,
                    }
                )
                any_saved = True
            except Exception as e:
                download_report.append(
                    {
                        "msg_id": msg_id,
                        "type": "attachment",
                        "name": filename,
                        "reject": f"attach_download_fail:{e}",
                    }
                )
                candidate.update({"decision": "error", "reason": f"attach_download_fail:{e}"})
                record_candidate(candidate)

        # ---- Links (אם לא ניצלנו מצורף) ----
        if not any_saved:
            html, plain = get_body_text(payload)
            links = links_from_message(html, plain)
            for u in links:
                candidate = {
                    "msg_id": msg_id,
                    "type": "link_direct_pdf",
                    "url": u,
                    "subject": subject,
                    "from": from_addr,
                    "receivedDateTime": received,
                }
                is_bezeq = within_domain(
                    u, ["myinvoice.bezeq.co.il", "my.bezeq.co.il", "bmy.bezeq.co.il"]
                )
                is_yes = within_domain(u, YES_DOMAINS)
                # הורדה ישירה אם PDF
                r = download_direct_pdf(
                    u,
                    referer="https://mail.google.com/",
                    ua=DEFAULT_BROWSER_UA,
                    verbose=args.debug,
                )
                if not r and is_yes:
                    browser_out = yes_fetch_with_browser(
                        u, headless=not args.bezeq_headful, verbose=args.debug
                    )
                    if browser_out.get("notes"):
                        candidate["notes"] = browser_out.get("notes")
                    if browser_out.get("ok"):
                        candidate["type"] = "link_browser_pdf"
                        r = (browser_out["name"], browser_out["blob"])
                if r:
                    name, blob = r
                    h = sha256_bytes(blob)
                    candidate.update({"name": name, "sha256": h})
                    if h in seen_hashes:
                        dup_path = hash_to_saved_path.get(h)
                        download_report.append(
                            {
                                "msg_id": msg_id,
                                "type": "link",
                                "url": u,
                                "skip": "duplicate_hash",
                                **({"duplicate_of": dup_path} if dup_path else {}),
                            }
                        )
                        candidate.update(
                            {
                                "decision": "skip",
                                "reason": "duplicate_hash",
                                **({"duplicate_of": dup_path} if dup_path else {}),
                            }
                        )
                        record_candidate(candidate)
                        continue
                    tmp_path = os.path.join(tmp_dir, f"tmp__{msg_tag}.pdf")
                    with open(tmp_path, "wb") as f:
                        f.write(blob)

                    trusted_hint = within_domain(u, TRUSTED_PROVIDERS) or is_municipal_text(
                        subject + " " + snippet
                    )
                    ok, stats = (True, {"pos_hits": 1, "neg_hits": 0})
                    if args.verify:
                        ok, stats = decide_pdf_relevance(tmp_path, trusted_hint=trusted_hint)
                    confidence = pdf_confidence(stats)
                    candidate.update(
                        {"stats": stats, "confidence": confidence, "trusted_hint": trusted_hint}
                    )

                    if not ok:
                        if quarant_dir:
                            out_q = ensure_unique_path(quarant_dir, name, tag=msg_tag)
                            os.replace(tmp_path, out_q)
                            download_report.append(
                                {
                                    "msg_id": msg_id,
                                    "type": "link",
                                    "url": u,
                                    "path": out_q,
                                    "ok": False,
                                    "stats": stats,
                                    "confidence": confidence,
                                }
                            )
                            candidate.update(
                                {"decision": "quarantine", "reason": "verify_failed", "path": out_q}
                            )
                        else:
                            os.remove(tmp_path)
                            download_report.append(
                                {
                                    "msg_id": msg_id,
                                    "type": "link",
                                    "url": u,
                                    "reject": "verify_failed",
                                    "stats": stats,
                                    "confidence": confidence,
                                }
                            )
                            candidate.update({"decision": "reject", "reason": "verify_failed"})
                        record_candidate(candidate)
                        continue

                    out_path = ensure_unique_path(inv_dir, name, tag=msg_tag)
                    os.replace(tmp_path, out_path)
                    seen_hashes.add(h)
                    hash_to_saved_path[h] = out_path
                    download_report.append(
                        {
                            "msg_id": msg_id,
                            "type": "link",
                            "url": u,
                            "path": out_path,
                            "ok": True,
                            "stats": stats,
                            "confidence": confidence,
                        }
                    )
                    candidate.update({"decision": "saved", "path": out_path})
                    record_candidate(candidate)
                    saved_rows.append(
                        {
                            "id": msg_id,
                            "subject": subject,
                            "from": from_addr,
                            "receivedDateTime": received,
                            "source": candidate.get("type", "link_direct_pdf"),
                            "path": out_path,
                        }
                    )
                    any_saved = True
                    break

                # בזק – Flutter
                if is_bezeq:
                    candidate = {
                        "msg_id": msg_id,
                        "type": "bezeq_api",
                        "url": u,
                        "subject": subject,
                        "from": from_addr,
                        "receivedDateTime": received,
                    }
                    out = bezeq_fetch_with_api_sniff(
                        url=u,
                        out_dir=inv_dir,
                        headless=not args.bezeq_headful,
                        keep_trace=args.bezeq_trace,
                        take_screens=args.bezeq_screenshots,
                        verbose=args.debug,
                    )
                    candidate["notes"] = out.get("notes", [])
                    if out.get("ok") and out.get("path"):
                        name, blob = out["path"]
                        h = sha256_bytes(blob)
                        candidate["sha256"] = h
                        if h in seen_hashes:
                            dup_path = hash_to_saved_path.get(h)
                            download_report.append(
                                {
                                    "msg_id": msg_id,
                                    "type": "link",
                                    "url": u,
                                    "skip": "duplicate_hash",
                                    **({"duplicate_of": dup_path} if dup_path else {}),
                                }
                            )
                            candidate.update(
                                {
                                    "decision": "skip",
                                    "reason": "duplicate_hash",
                                    **({"duplicate_of": dup_path} if dup_path else {}),
                                }
                            )
                            record_candidate(candidate)
                            continue

                        tmp_path = os.path.join(tmp_dir, f"tmp__{msg_tag}.pdf")
                        with open(tmp_path, "wb") as f:
                            f.write(blob)

                        trusted_hint = True
                        if args.verify:
                            ok, stats = decide_pdf_relevance(tmp_path, trusted_hint=trusted_hint)
                        else:
                            ok, stats = True, {"pos_hits": 1, "neg_hits": 0}
                        confidence = pdf_confidence(stats)
                        candidate.update(
                            {
                                "stats": stats,
                                "confidence": confidence,
                                "trusted_hint": trusted_hint,
                            }
                        )

                        if not ok:
                            if quarant_dir:
                                out_q = ensure_unique_path(quarant_dir, name, tag=msg_tag)
                                os.replace(tmp_path, out_q)
                                download_report.append(
                                    {
                                        "msg_id": msg_id,
                                        "type": "link",
                                        "url": u,
                                        "path": out_q,
                                        "ok": False,
                                        "stats": stats,
                                        "notes": out.get("notes", []),
                                        "confidence": confidence,
                                    }
                                )
                                candidate.update(
                                    {
                                        "decision": "quarantine",
                                        "reason": "verify_failed",
                                        "path": out_q,
                                    }
                                )
                            else:
                                os.remove(tmp_path)
                                download_report.append(
                                    {
                                        "msg_id": msg_id,
                                        "type": "link",
                                        "url": u,
                                        "reject": "verify_failed",
                                        "stats": stats,
                                        "notes": out.get("notes", []),
                                        "confidence": confidence,
                                    }
                                )
                                candidate.update({"decision": "reject", "reason": "verify_failed"})
                            record_candidate(candidate)
                            continue

                        out_path = ensure_unique_path(inv_dir, name, tag=msg_tag)
                        os.replace(tmp_path, out_path)
                        seen_hashes.add(h)
                        hash_to_saved_path[h] = out_path
                        download_report.append(
                            {
                                "msg_id": msg_id,
                                "type": "link",
                                "url": u,
                                "path": out_path,
                                "ok": True,
                                "stats": stats,
                                "notes": out.get("notes", []),
                                "confidence": confidence,
                            }
                        )
                        candidate.update({"decision": "saved", "path": out_path})
                        record_candidate(candidate)
                        saved_rows.append(
                            {
                                "id": msg_id,
                                "subject": subject,
                                "from": from_addr,
                                "receivedDateTime": received,
                                "source": "bezeq_api",
                                "path": out_path,
                            }
                        )
                        any_saved = True
                        break
                    else:
                        if out.get("notes"):
                            download_report.append(
                                {
                                    "msg_id": msg_id,
                                    "type": "link",
                                    "url": u,
                                    "notes": out.get("notes", []),
                                    "ok": False,
                                    "reject": "bezeq_no_pdf",
                                }
                            )
                        candidate.update({"decision": "no_pdf", "reason": "bezeq_no_pdf"})
                        record_candidate(candidate)
                    continue

                candidate.update({"decision": "download_failed"})
                record_candidate(candidate)
                continue

            if not any_saved and links:
                record_nonmatch(
                    {
                        "id": msg_id,
                        "subject": subject,
                        "from": from_addr,
                        "receivedDateTime": received,
                        "reason": "links_no_pdf",
                    }
                )
                message_rejected = True

        if not any_saved and not message_rejected:
            record_nonmatch(
                {
                    "id": msg_id,
                    "subject": subject,
                    "from": from_addr,
                    "receivedDateTime": received,
                    "reason": "no_attach_no_pdf_links",
                }
            )

    # ----- Reports -----
    if args.download_report:
        with open(args.download_report, "w", encoding="utf-8") as f:
            json.dump(
                {"saved": saved_rows, "rejected": rejected_rows, "ts": now_utc_iso()},
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"Download report → {args.download_report}")

    if args.save_json:
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(saved_rows, f, ensure_ascii=False, indent=2)
        print(f"Saved messages JSON → {args.save_json}")

    if args.save_csv:
        fields = ["id", "subject", "from", "receivedDateTime", "source", "path"]
        with open(args.save_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in saved_rows:
                w.writerow({k: r.get(k) for k in fields})
        print(f"Saved messages CSV → {args.save_csv}")

    if args.save_candidates:
        with open(args.save_candidates, "w", encoding="utf-8") as f:
            json.dump(candidate_entries, f, ensure_ascii=False, indent=2)
        print(f"Saved candidates → {args.save_candidates}")

    if args.save_nonmatches:
        with open(args.save_nonmatches, "w", encoding="utf-8") as f:
            json.dump(rejected_rows, f, ensure_ascii=False, indent=2)
        print(f"Saved nonmatches → {args.save_nonmatches}")

    print(f"Done. Saved {len(saved_rows)} invoices; Rejected {len(rejected_rows)}.")


if __name__ == "__main__":
    main()
