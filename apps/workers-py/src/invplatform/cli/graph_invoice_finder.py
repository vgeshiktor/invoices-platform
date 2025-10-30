#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graph_invoice_finder.v3.9.2.py
==============================

שינויים בגרסה זו:
- דגל חדש: --exclude-sent
  מחפש את מזהה תיקיית Sent Items ומוסיף למסנן: parentFolderId ne '<id>'.
  כך אנחנו לא עוברים על הודעות שנשלחו.

- כל היכולות מ-v3.9.1a נשמרו:
  * אין דריסה של קבצים (שם ייחודי + hash dedup).
  * אימות רלוונטיות PDF בעזרת PyMuPDF (חיובי/שלילי).
  * צמצום FP (הסרת "statement" מחיובי; הוספת שליליים כמו תלושי שכר).
  * מיקוד עיריות/ארנונה.
  * הורדת בזק דרך Playwright ע"י ניטור קריאות API (GetAttachedInvoiceById)
    והורדת ה-PDF ישירות, כולל הוספת InvoiceId לשם הקובץ אם קיים.

תלויות:
    pip install msal requests playwright beautifulsoup4 lxml pymupdf
    playwright install chromium

דוגמאות:
    python -m invplatform.cli.graph_invoice_finder \
      --client-id "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" \
      --authority consumers \
      --start-date 2025-09-01 --end-date 2025-10-01 \
      --invoices-dir invoices_out \
      --exclude-sent \
      --verify \
      --save-json invoices.json --save-csv invoices.csv \
      --download-report download_report.json \
      --bezeq-trace --bezeq-screenshots

    # דיבוג מוגבר + חלון דפדפן ל-Flutter של בזק:
    python -m invplatform.cli.graph_invoice_finder \
      --client-id "..." --authority consumers \
      --start-date 2025-09-01 --end-date 2025-10-01 \
      --invoices-dir invoices_out \
      --exclude-sent \
      --verify --debug --bezeq-headful --bezeq-trace --bezeq-screenshots
"""

import argparse
import csv
import datetime as dt
import json
import logging
import os
import re
import sys
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlparse

import msal
import requests
from bs4 import BeautifulSoup

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from ..domain import constants as domain_constants
from ..domain import files as domain_files
from ..domain import pdf as domain_pdf
from ..domain import relevance as domain_relevance


# ---------- Utils ----------
ensure_dir = domain_files.ensure_dir
sanitize_filename = domain_files.sanitize_filename
short_msg_tag = domain_files.short_msg_tag
ensure_unique_path = domain_files.ensure_unique_path
sha256_bytes = domain_files.sha256_bytes
keyword_in_text = domain_relevance.keyword_in_text
within_domain = domain_relevance.within_domain


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def now_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")


# ---------- Keywords ----------
EN_POS = domain_constants.EN_POS
HEB_POS = domain_constants.HEB_POS
EN_NEG = domain_constants.EN_NEG
HEB_NEG = domain_constants.HEB_NEG
TRUSTED_PROVIDERS = domain_constants.TRUSTED_PROVIDERS
HEB_MUNICIPAL = domain_constants.HEB_MUNICIPAL


# ---------- PDF verification ----------
pdf_keyword_stats = domain_pdf.pdf_keyword_stats
pdf_confidence = domain_pdf.pdf_confidence


is_municipal_text = domain_relevance.is_municipal_text
body_has_negative = domain_relevance.body_has_negative
body_has_positive = domain_relevance.body_has_positive


# ---------- Graph client ----------
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphClient:
    def __init__(
        self,
        client_id: str,
        authority: str = "consumers",
        scopes: Optional[List[str]] = None,
    ):
        self.client_id = client_id
        self.authority = f"https://login.microsoftonline.com/{authority}"
        self.scopes = scopes or ["User.Read", "Mail.Read"]
        self.session = requests.Session()
        self.token = self._acquire_token_device_code()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _acquire_token_device_code(self) -> str:
        app = msal.PublicClientApplication(self.client_id, authority=self.authority)
        flow = app.initiate_device_flow(scopes=self.scopes)
        if "user_code" not in flow:
            raise RuntimeError("MSAL device flow init failed")
        print("== Device Code Authentication ==")
        print(flow["message"])
        res = app.acquire_token_by_device_flow(flow)
        if "access_token" not in res:
            raise RuntimeError(f"MSAL failed: {res}")
        return res["access_token"]

    def get(self, url: str, params: dict = None, headers: dict = None) -> dict:
        h = dict(headers or {})
        r = self.session.get(url, params=params or {}, headers=h)
        if r.status_code >= 400:
            raise RuntimeError(f"Graph GET failed {r.status_code}: {r.text}")
        return r.json()

    # חדש: אחזור מזהה תיקייה ידועה (inbox, sentitems, drafts, וכו')
    def get_wellknown_folder_id(self, wellknown: str) -> Optional[str]:
        url = f"{GRAPH_BASE}/me/mailFolders/{wellknown}"
        try:
            data = self.get(url, params={"$select": "id"})
            return data.get("id")
        except Exception:
            return None

    # שינוי: תמיכה בהחרגת תיקיות דרך parentFolderId
    def iter_messages(
        self,
        start_iso: str,
        end_iso: str,
        page_size: int = 50,
        max_pages: int = 50,
        exclude_parent_ids: Optional[List[str]] = None,
    ):
        url = f"{GRAPH_BASE}/me/messages"
        base_filter = f"receivedDateTime ge {start_iso} and receivedDateTime lt {end_iso}"
        if exclude_parent_ids:
            for fid in exclude_parent_ids:
                if fid:
                    base_filter += f" and parentFolderId ne '{fid}'"
        params = {
            "$filter": base_filter,
            "$select": "id,subject,from,receivedDateTime,hasAttachments,webLink,bodyPreview,parentFolderId",
            "$orderby": "receivedDateTime desc",
            "$top": str(page_size),
        }
        page = 0
        while True:
            data = self.get(url, params=params if page == 0 else None)
            for it in data.get("value", []):
                yield it
            n = data.get("@odata.nextLink")
            if not n or page + 1 >= max_pages:
                break
            url = n
            page += 1

    def get_message_body_html(self, msg_id: str) -> str:
        url = f"{GRAPH_BASE}/me/messages/{msg_id}?$select=body"
        data = self.get(url)
        return ((data.get("body") or {}).get("content")) or ""

    def list_attachments(self, msg_id: str) -> List[dict]:
        url = f"{GRAPH_BASE}/me/messages/{msg_id}/attachments"
        data = self.get(url, params={"$top": "50", "$select": "id,name,contentType,size,isInline"})
        return data.get("value", [])

    def download_attachment(self, msg_id: str, att_id: str) -> bytes:
        url = f"{GRAPH_BASE}/me/messages/{msg_id}/attachments/{att_id}/$value"
        r = self.session.get(url)
        if r.status_code >= 400:
            raise RuntimeError(f"Graph GET attach failed {r.status_code}: {r.text}")
        return r.content


# ---------- HTML/links ----------
def extract_links_from_html(html: str) -> List[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        links.append(a["href"])
    return list(dict.fromkeys(links))


# ---------- Direct PDF via requests ----------
def download_direct_pdf(
    url: str, out_dir: str, referer: Optional[str] = None, ua: Optional[str] = None
) -> Optional[Tuple[str, bytes]]:
    headers = {}
    if referer:
        headers["Referer"] = referer
    if ua:
        headers["User-Agent"] = ua
    try:
        r = requests.get(url, headers=headers, timeout=30)
        ct = (r.headers.get("Content-Type") or "").lower()
        if r.status_code == 200 and ("pdf" in ct or url.lower().endswith(".pdf")):
            name = "link_invoice.pdf"
            cd = r.headers.get("Content-Disposition") or ""
            m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, flags=re.I)
            if m:
                name = sanitize_filename(m.group(1))
                if not name.lower().endswith(".pdf"):
                    name += ".pdf"
            return name, r.content
    except Exception:
        pass
    return None


# ---------- Bezeq (Playwright) ----------
def normalize_myinvoice_url(u: str) -> str:
    s = (u or "").strip()
    s = s.replace("\\?", "?").replace("\\&", "&").replace("\\=", "=")
    s = s.replace("://myinvoice.bezeq.co.il//?", "://myinvoice.bezeq.co.il/?")
    s = re.sub(r"(://myinvoice\.bezeq\.co\.il)/+(?=\?)", r"\1/", s)
    return s


def bezeq_fetch_with_api_sniff(
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

        try:
            page.goto(normalized_url, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle", timeout=12000)
        except PWTimeout:
            note("networkidle_timeout")

        # הורדה ישירה מה-API
        def direct_api(u: str) -> Optional[Tuple[str, bytes]]:
            try:
                resp = context.request.get(u, headers={"Referer": normalized_url})
                body = resp.body()
                ct = (resp.headers.get("content-type") or "").lower()
                if (ct and "pdf" in ct) or body[:4] == b"%PDF":
                    name = "bezeq_invoice_api.pdf"
                    # ננסה להוסיף InvoiceId לשם
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

        # אם כבר נתפסו URL-ים – ננסה
        for u in list(dict.fromkeys(api_urls)):
            r = direct_api(u)
            if r:
                name, blob = r
                res["ok"] = True
                res["path"] = (name, blob)
                break

        # טריגר עדין (למקרה שלא נתפס מייד)
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


# ---------- Flow helpers ----------
def should_consider_message(subject: str, preview: str) -> bool:
    t = f"{subject or ''} {preview or ''}"
    if body_has_negative(t):
        return False
    # חיובי או ארנונה
    return body_has_positive(t) or is_municipal_text(t)


def decide_pdf_relevance(path: str, trusted_hint: bool = False) -> Tuple[bool, Dict]:
    stats = pdf_keyword_stats(path)
    pos_hits = stats.get("pos_hits", 0) or 0
    neg_terms = list(stats.get("neg_terms", []))
    if trusted_hint:
        allowed_neg = {"שכר"}
        filtered_neg = [t for t in neg_terms if t not in allowed_neg]
    else:
        filtered_neg = neg_terms
    neg_hits_effective = len(filtered_neg)
    # כלל: חייבים לפחות hit חיובי אחד וללא שלילות
    ok = pos_hits >= 1 and neg_hits_effective == 0
    # ריכוך: אם מקור מהימן ואין שלילות משמעותיות, נוכל לאשר גם ללא hit חיובי
    if trusted_hint and neg_hits_effective == 0 and pos_hits == 0:
        ok = True
    return ok, stats


# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(
        description="Graph Invoice Finder v3.9.2 (exclude sent + strict relevance)"
    )
    ap.add_argument("--client-id", required=True)
    ap.add_argument("--authority", default="consumers")
    ap.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end-date", required=True, help="YYYY-MM-DD (exclusive)")

    ap.add_argument("--invoices-dir", default="./invoices_out")
    ap.add_argument("--keep-quarantine", action="store_true")
    ap.add_argument("--download-report", default="download_report.json")
    ap.add_argument("--save-json", default=None)
    ap.add_argument("--save-csv", default=None)
    ap.add_argument("--save-candidates", default=None)
    ap.add_argument("--save-nonmatches", default=None)

    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--explain", action="store_true")
    ap.add_argument(
        "--threshold-sweep",
        default=None,
        help="Comma-separated confidence thresholds (e.g. 0.2,0.5,0.8)",
    )

    # חדש: החרגה של Sent
    ap.add_argument(
        "--exclude-sent",
        action="store_true",
        help="אל תכלול הודעות מתיקיית הפריטים שנשלחו (Sent Items)",
    )

    # דגלים ל-Bezeq/Playwright
    ap.add_argument("--bezeq-headful", action="store_true")
    ap.add_argument("--bezeq-trace", action="store_true")
    ap.add_argument("--bezeq-screenshots", action="store_true")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(message)s")

    inv_dir = ensure_dir(args.invoices_dir)
    quarant_dir = ensure_dir(os.path.join(inv_dir, "quarantine")) if args.keep_quarantine else None
    tmp_dir = ensure_dir(os.path.join(inv_dir, "_tmp"))

    try:
        start_dt = dt.datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
        end_dt = dt.datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        print("פורמט תאריך לא תקין. השתמשו ב-YYYY-MM-DD")
        sys.exit(3)
    start_iso, end_iso = start_dt.isoformat(), end_dt.isoformat()

    gc = GraphClient(client_id=args.client_id, authority=args.authority)

    # אוסף תיקיות להחרגה
    exclude_ids: List[str] = []
    if args.exclude_sent:
        sent_id = gc.get_wellknown_folder_id("sentitems")
        if sent_id:
            exclude_ids.append(sent_id)

    saved_rows: List[Dict] = []
    rejected_rows: List[Dict] = []
    download_report: List[Dict] = []
    candidate_entries: List[Dict] = []
    saved_confidences: List[float] = []
    seen_hashes: Set[str] = set()
    hash_to_saved_path: Dict[str, str] = {}
    processed_msg_ids: Set[str] = set()

    def record_candidate(entry: Dict):
        if args.save_candidates:
            candidate_entries.append(entry)
        if args.explain:
            label = entry.get("name") or entry.get("url") or entry.get("type")
            decision = entry.get("decision")
            reason = entry.get("reason")
            confidence = entry.get("confidence")
            parts: List[str] = []
            if decision:
                parts.append(str(decision))
            if reason:
                parts.append(str(reason))
            if confidence is not None:
                parts.append(f"conf={confidence:.2f}")
            logging.info(
                "    candidate[%s] %s => %s",
                entry.get("type"),
                label,
                ", ".join(parts) if parts else "recorded",
            )

    msg_idx = 0
    for msg in gc.iter_messages(
        start_iso, end_iso, page_size=50, max_pages=50, exclude_parent_ids=exclude_ids
    ):
        msg_idx += 1
        msg_id = msg.get("id")
        if msg_id in processed_msg_ids:
            if args.explain:
                logging.info("Skip duplicate message %s", msg_id)
            continue
        processed_msg_ids.add(msg_id)
        subject = msg.get("subject") or ""
        preview = msg.get("bodyPreview") or ""
        from_addr = ((msg.get("from") or {}).get("emailAddress") or {}).get("address") or ""
        received = msg.get("receivedDateTime")
        web_link = msg.get("webLink")
        has_attachments = bool(msg.get("hasAttachments"))

        # מסנן ראשוני: אל תתעסק עם הודעות שליליות/לא קשורות
        if not (has_attachments or should_consider_message(subject, preview)):
            continue

        logging.info(f"[{msg_idx}] {subject} | {from_addr} | {received}")

        any_saved = False
        msg_tag = short_msg_tag(msg_id)
        msg_context = f"{subject} {preview}"
        msg_trusted_hint = is_municipal_text(msg_context)

        def record_rejection(reason: str) -> None:
            entry = {
                "id": msg_id,
                "subject": subject,
                "from": from_addr,
                "receivedDateTime": received,
                "webLink": web_link,
                "preview": preview,
                "reason": reason,
            }
            rejected_rows.append(entry)
            if args.explain:
                logging.info("    message_reject: %s", reason)

        # ---- A) Attachments ----
        atts = []
        if has_attachments:
            try:
                atts = gc.list_attachments(msg_id)
            except Exception as e:
                record_rejection(f"attachments_list_fail:{e}")

        for a in atts:
            ct = (a.get("contentType") or "").lower()
            name = a.get("name") or "file.pdf"
            if "pdf" not in ct and not name.lower().endswith(".pdf"):
                continue
            candidate = {
                "msg_id": msg_id,
                "type": "attachment",
                "name": name,
                "contentType": ct,
            }
            try:
                blob = gc.download_attachment(msg_id, a["id"])
                h = sha256_bytes(blob)
                candidate["sha256"] = h
                if h in seen_hashes:
                    dup_path = hash_to_saved_path.get(h)
                    download_report.append(
                        {
                            "msg_id": msg_id,
                            "type": "attachment",
                            "name": name,
                            "skip": "duplicate_hash",
                            **({"duplicate_of": dup_path} if dup_path else {}),
                        }
                    )
                    if dup_path:
                        candidate.update(
                            {
                                "decision": "skip",
                                "reason": "duplicate_hash",
                                "duplicate_of": dup_path,
                            }
                        )
                    else:
                        candidate.update({"decision": "skip", "reason": "duplicate_hash"})
                    record_candidate(candidate)
                    continue
                # כתיבה זמנית
                tmp_path = os.path.join(tmp_dir, f"tmp__{msg_tag}.pdf")
                with open(tmp_path, "wb") as f:
                    f.write(blob)

                trusted_hint = msg_trusted_hint  # הקשר המייל (למשל עירייה/מים)
                ok = True
                stats = {"pos_hits": 1, "neg_hits": 0, "pos_terms": [], "neg_terms": []}
                if args.verify:
                    ok, stats = decide_pdf_relevance(tmp_path, trusted_hint=trusted_hint)

                confidence = pdf_confidence(stats)
                candidate.update({"stats": stats, "confidence": confidence})

                if not ok:
                    if quarant_dir:
                        out_q = ensure_unique_path(quarant_dir, name, tag=msg_tag)
                        os.replace(tmp_path, out_q)
                        download_report.append(
                            {
                                "msg_id": msg_id,
                                "type": "attachment",
                                "name": name,
                                "path": out_q,
                                "ok": False,
                                "stats": stats,
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
                                "type": "attachment",
                                "name": name,
                                "reject": "verify_failed",
                                "stats": stats,
                                "confidence": confidence,
                            }
                        )
                        candidate.update({"decision": "reject", "reason": "verify_failed"})
                    record_candidate(candidate)
                    continue

                # קבע שם ייחודי (לא לדרוס)
                out_path = ensure_unique_path(inv_dir, name, tag=msg_tag)
                os.replace(tmp_path, out_path)
                seen_hashes.add(h)
                hash_to_saved_path[h] = out_path
                download_report.append(
                    {
                        "msg_id": msg_id,
                        "type": "attachment",
                        "name": name,
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
                        "webLink": web_link,
                        "stats": stats,
                        "confidence": confidence,
                    }
                )
                saved_confidences.append(confidence)
                any_saved = True

            except Exception as e:
                err = f"attach_download_fail:{e}"
                download_report.append(
                    {
                        "msg_id": msg_id,
                        "type": "attachment",
                        "name": name,
                        "reject": err,
                    }
                )
                candidate.update({"decision": "error", "reason": err})
                record_candidate(candidate)

        # ---- B) Links ----
        if not any_saved:
            try:
                html = gc.get_message_body_html(msg_id)
            except Exception as e:
                html = ""
                download_report.append(
                    {"msg_id": msg_id, "type": "body", "reject": f"body_fetch_fail:{e}"}
                )

            links = extract_links_from_html(html)
            for u in links:
                # הורדה ישירה אם PDF
                r = download_direct_pdf(u, inv_dir, referer=web_link, ua="Mozilla/5.0")
                if r:
                    name, blob = r
                    candidate = {
                        "msg_id": msg_id,
                        "type": "link_direct",
                        "url": u,
                        "name": name,
                    }
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
                        if dup_path:
                            candidate.update(
                                {
                                    "decision": "skip",
                                    "reason": "duplicate_hash",
                                    "duplicate_of": dup_path,
                                }
                            )
                        else:
                            candidate.update({"decision": "skip", "reason": "duplicate_hash"})
                        record_candidate(candidate)
                        continue
                    # כתיבה זמנית + אימות
                    tmp_path = os.path.join(tmp_dir, f"tmp__{msg_tag}.pdf")
                    with open(tmp_path, "wb") as f:
                        f.write(blob)

                    trusted_hint = bool(
                        within_domain(u, TRUSTED_PROVIDERS)
                        or msg_trusted_hint
                        or is_municipal_text(msg_context)
                    )
                    ok = True
                    stats = {
                        "pos_hits": 1,
                        "neg_hits": 0,
                        "pos_terms": [],
                        "neg_terms": [],
                    }
                    if args.verify:
                        ok, stats = decide_pdf_relevance(tmp_path, trusted_hint=trusted_hint)

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
                            "trusted_hint": trusted_hint,
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
                            "source": "link_direct_pdf",
                            "path": out_path,
                            "webLink": web_link,
                            "url": u,
                            "stats": stats,
                            "confidence": confidence,
                            "trusted_hint": trusted_hint,
                        }
                    )
                    saved_confidences.append(confidence)
                    any_saved = True
                    break

                # בזק – Flutter
                if within_domain(u, ["myinvoice.bezeq.co.il", "my.bezeq.co.il", "bmy.bezeq.co.il"]):
                    out = bezeq_fetch_with_api_sniff(
                        url=u,
                        out_dir=inv_dir,
                        headless=not args.bezeq_headful,
                        keep_trace=args.bezeq_trace,
                        take_screens=args.bezeq_screenshots,
                        verbose=args.debug,
                    )
                    candidate = {
                        "msg_id": msg_id,
                        "type": "link_bezeq",
                        "url": u,
                        "notes": out.get("notes", []),
                    }
                    if out.get("ok") and out.get("path"):
                        name, blob = out["path"]
                        h = sha256_bytes(blob)
                        candidate["name"] = name
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
                            if dup_path:
                                candidate.update(
                                    {
                                        "decision": "skip",
                                        "reason": "duplicate_hash",
                                        "duplicate_of": dup_path,
                                    }
                                )
                            else:
                                candidate.update({"decision": "skip", "reason": "duplicate_hash"})
                            record_candidate(candidate)
                            continue

                        tmp_path = os.path.join(tmp_dir, f"tmp__{msg_tag}.pdf")
                        with open(tmp_path, "wb") as f:
                            f.write(blob)

                        trusted_hint = True  # בזק – ספק אמין
                        ok = True
                        stats = {
                            "pos_hits": 1,
                            "neg_hits": 0,
                            "pos_terms": [],
                            "neg_terms": [],
                        }
                        if args.verify:
                            ok, stats = decide_pdf_relevance(tmp_path, trusted_hint=trusted_hint)

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
                                "webLink": web_link,
                                "url": u,
                                "stats": stats,
                                "confidence": confidence,
                                "trusted_hint": trusted_hint,
                                "notes": out.get("notes", []),
                            }
                        )
                        saved_confidences.append(confidence)
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

            if not any_saved and links:
                record_rejection("links_no_pdf")

        if not any_saved and not has_attachments:
            record_rejection("no_attach_no_pdf_links")

    # ----- Reports -----
    if args.threshold_sweep:
        try:
            thresholds = [
                float(x.strip()) for x in (args.threshold_sweep or "").split(",") if x.strip()
            ]
            if thresholds:
                if saved_confidences:
                    print("\nThreshold sweep on saved invoices:")
                    for t in sorted(thresholds):
                        count = sum(1 for c in saved_confidences if c >= t)
                        print(f"  >= {t:.2f}: {count}")
                else:
                    print("\nThreshold sweep requested, but no saved invoices.")
        except Exception as e:
            print(f"threshold_sweep parse error: {e}")

    if args.download_report:
        with open(args.download_report, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "saved": saved_rows,
                    "rejected": rejected_rows,
                    "report": download_report,
                    "ts": now_utc_iso(),
                },
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
        fields = [
            "id",
            "subject",
            "from",
            "receivedDateTime",
            "source",
            "path",
            "webLink",
        ]
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
