#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graph_invoice_finder.v3.9.py
============================

מטרה
-----
סורק דוא"ל דרך Microsoft Graph, מאתר חשבוניות/קבלות:
- קבצי PDF מצורפים יורדים ישירות מ-Graph.
- הודעות בלי קובץ אך עם לינק: מנסה להוריד PDF ישירות.
- מקרה ייחודי לבזק (myinvoice.bezeq.co.il / my.bezeq.co.il / bmy.bezeq.co.il):
  לוכד את קריאת ה-API "GetAttachedInvoiceById" דרך Playwright ומוריד את ה-PDF ישירות,
  גם אם כפתור "להורדה" הוא אלמנט Flutter/Canvas.

כולל אימות PDF עם PyMuPDF (מילות מפתח באנגלית/עברית), דוחות JSON/CSV, ו-"karantina"
לקבצים שלא עברו אימות. כל ההערות והוראות ההפעלה *כאן* בקובץ.

תלויות
------
pip install msal requests playwright beautifulsoup4 lxml pymupdf
playwright install chromium

דוגמאות הפעלה
--------------
# התחברות ב-Device Code, חלון Playwright נסתר, עם אימות PDF, ושמירת דוחות:
python graph_invoice_finder.v3.9.py \
  --client-id "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" \
  --authority consumers \
  --start-date 2025-09-01 --end-date 2025-10-01 \
  --invoices-dir invoices_out \
  --save-json invoices.json --save-csv invoices.csv \
  --download-report download_report.json \
  --verify \
  --bezeq-trace --bezeq-screenshots

# דיבוג מוגבר (כולל חלון דפדפן) רק ללינקים (לא ישפיע אם אין בזק):
python graph_invoice_finder.v3.9.py \
  --client-id "..." --authority consumers \
  --start-date 2025-09-01 --end-date 2025-10-01 \
  --invoices-dir invoices_out \
  --verify --debug --bezeq-headful --bezeq-trace --bezeq-screenshots

מה נשמר
--------
- invoices_out/                      # קבצי PDF שעברו אימות
- invoices_out/quarantine/           # קבצים/הורדות שנכשלו באימות (אם --keep-quarantine)
- download_report.json               # רשימת הורדות/סיבות דחייה
- invoices.json / invoices.csv       # שורות הודעות שאותרו כחשבוניות (אם נתת --save-*)

הערות חשובות
-------------
* Graph: נמנעים מ-$search יחד עם $filter (שגיאת SearchWithFilter) ומ-$select עם '@odata.type'.
* בברירת מחדל שואבים עד ~1000 הודעות בטווח התאריכים, ומסננים לוקאלית לפי מילות מפתח.
* בזק: אין תלות ב"קליק"; אם נמצא URL GetAttachedInvoiceById – מורידים ישירות ב-HTTP client
  של Playwright (עם Referer מתאים).

"""

import argparse
import csv
import datetime as dt
import json
import logging
import os
import pathlib
import re
import sys
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

import msal
import requests

# ------- אימות PDF עם PyMuPDF -------
try:
    import fitz  # PyMuPDF

    HAVE_PYMUPDF = True
except Exception:
    HAVE_PYMUPDF = False

# ------- HTML parsing -------
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PWTimeout

# ------- Playwright (נטען דינמית כאשר צריך) -------
from playwright.sync_api import sync_playwright


# ==========================
# עזרי קבצים/זמן/טקסט
# ==========================
def ensure_dir(p: str) -> str:
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)
    return p


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def now_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")


def sanitize_filename(name: str, default: str = "invoice.pdf") -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "_", (name or "").strip())
    return name or default


def within_domain(u: str, domains: List[str]) -> bool:
    try:
        host = urlparse(u).hostname or ""
        return any(host.endswith(d) for d in domains)
    except Exception:
        return False


# ==========================
# אימות PDF בסיסי
# ==========================
HEB_KEYWORDS = [
    "חשבונית",
    "קבלה",
    "חשבונית מס",
    "חשבונית מס קבלה",
    "ארנונה",
    "שובר תשלום",
    "דרישת תשלום",
    "אגרת",
    "היטל",
]
EN_KEYWORDS = ["invoice", "tax invoice", "receipt", "bill", "statement"]


def verify_pdf_text(path: str, min_hits: int = 1) -> bool:
    if not HAVE_PYMUPDF:
        # אם אין PyMuPDF—נחשיב כדין (אפשר לשנות ל-False אם מעדיפים להחמיר)
        return True
    try:
        doc = fitz.open(path)
        hits = 0
        for page in doc:
            text = page.get_text("text") or ""
            t = text.lower()
            if any(k.lower() in t for k in EN_KEYWORDS):
                hits += 1
            # עברית לא נוריד ל-lower (זהה), נחפש כמו שהוא
            if any(k in text for k in HEB_KEYWORDS):
                hits += 1
            if hits >= min_hits:
                return True
        return False
    except Exception:
        return False


# ==========================
# Microsoft Graph
# ==========================
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphClient:
    def __init__(
        self,
        client_id: str,
        authority: str = "consumers",
        scopes: Optional[List[str]] = None,
    ):
        self.client_id = client_id
        # authority יכול להיות: "consumers"|"organizations"|tenant-id
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
        result = app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            raise RuntimeError(f"MSAL failed: {result}")
        return result["access_token"]

    def get(self, url: str, params: dict = None, headers: dict = None) -> dict:
        h = dict(headers or {})
        r = self.session.get(url, params=params or {}, headers=h)
        if r.status_code >= 400:
            raise RuntimeError(f"Graph GET failed {r.status_code}: {r.text}")
        return r.json()

    def iter_messages(
        self, start_iso: str, end_iso: str, max_pages: int = 50, page_size: int = 50
    ):
        """
        שואב הודעות בטווח תאריכים לפי receivedDateTime (filter בלבד, ללא $search).
        """
        url = f"{GRAPH_BASE}/me/messages"
        params = {
            # filter פשוט ויעיל (נמנע מ-InefficientFilter)
            "$filter": f"receivedDateTime ge {start_iso} and receivedDateTime lt {end_iso}",
            "$select": "id,subject,from,receivedDateTime,hasAttachments,webLink,bodyPreview",
            "$orderby": "receivedDateTime desc",
            "$top": str(page_size),
        }
        page = 0
        while True:
            data = self.get(url, params=params if page == 0 else None)
            value = data.get("value", [])
            for item in value:
                yield item
            next_url = data.get("@odata.nextLink")
            if not next_url or page + 1 >= max_pages:
                break
            url = next_url
            page += 1

    def get_message_body_html(self, msg_id: str) -> str:
        url = f"{GRAPH_BASE}/me/messages/{msg_id}?$select=body"
        data = self.get(url)
        body = (data.get("body") or {}).get("content") or ""
        return body

    def list_attachments(self, msg_id: str) -> List[dict]:
        url = f"{GRAPH_BASE}/me/messages/{msg_id}/attachments"
        data = self.get(
            url, params={"$top": "50", "$select": "id,name,contentType,size,isInline"}
        )
        return data.get("value", [])

    def download_attachment(self, msg_id: str, att_id: str) -> bytes:
        url = f"{GRAPH_BASE}/me/messages/{msg_id}/attachments/{att_id}/$value"
        r = self.session.get(url)
        if r.status_code >= 400:
            raise RuntimeError(f"Graph GET attach failed {r.status_code}: {r.text}")
        return r.content


# ==========================
# הורדת לינקים כללית
# ==========================
def extract_links_from_html(html: str) -> List[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        links.append(a["href"])
    # ייתכנו קישורים בג'אווהסקריפט – נשאיר לפתרון ספציפי (בזק)
    return list(dict.fromkeys(links))


def download_direct_pdf(
    url: str, out_dir: str, referer: Optional[str] = None, ua: Optional[str] = None
) -> Optional[str]:
    """
    מנסה להוריד ישירות אם ה-URL מסתיים ב-PDF או שיש content-type PDF.
    """
    headers = {}
    if referer:
        headers["Referer"] = referer
    if ua:
        headers["User-Agent"] = ua
    try:
        r = requests.get(url, headers=headers, timeout=30, stream=True)
        ct = (r.headers.get("Content-Type") or "").lower()
        if r.status_code == 200 and ("pdf" in ct or url.lower().endswith(".pdf")):
            name = "link_invoice.pdf"
            cd = r.headers.get("Content-Disposition") or ""
            m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, flags=re.I)
            if m:
                name = sanitize_filename(m.group(1))
                if not name.lower().endswith(".pdf"):
                    name += ".pdf"
            out_path = os.path.join(out_dir, name)
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(1024 * 128):
                    if chunk:
                        f.write(chunk)
            return out_path
    except Exception:
        pass
    return None


# ==========================
# פתרון ייעודי: בזק (Playwright)
# ==========================
def normalize_myinvoice_url(u: str) -> str:
    s = (u or "").strip()
    s = s.replace("\\?", "?").replace("\\&", "&").replace("\\=", "=")
    s = s.replace("://myinvoice.bezeq.co.il//?", "://myinvoice.bezeq.co.il/?")
    s = re.sub(r"(://myinvoice\.bezeq\.co\.il)/+(?=\?)", r"\1/", s)
    return s


def bezeq_fetch_with_api_sniff(
    url: str,
    out_dir: str,
    headless: bool = True,
    keep_trace: bool = True,
    take_screens: bool = True,
    verbose: bool = False,
) -> Dict:
    """
    פותר בזק: לוכד את קריאת GetAttachedInvoiceById ומוריד ישירות.
    """
    res = {"ok": False, "path": None, "notes": [], "normalized_url": None}

    def note(m: str):
        if verbose:
            print(m)
        res["notes"].append(m)

    normalized_url = normalize_myinvoice_url(url)
    res["normalized_url"] = normalized_url
    if normalized_url != url:
        note(f"url_normalized_from:{url}")
        note(f"url_normalized_to:{normalized_url}")

    screens_dir = ensure_dir(os.path.join(out_dir, "screens"))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless, args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            accept_downloads=True,
            locale="he-IL",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7"
            },
        )
        if keep_trace:
            context.tracing.start(screenshots=True, snapshots=True, sources=False)

        api_urls: List[str] = []

        def on_console(msg):
            try:
                t = (
                    msg.type()
                    if callable(getattr(msg, "type", None))
                    else str(getattr(msg, "type", ""))
                )
                x = (
                    msg.text()
                    if callable(getattr(msg, "text", None))
                    else str(getattr(msg, "text", ""))
                )
                note(f"console:{t}:{x}")
                if "GetAttachedInvoiceById" in x:
                    m = re.search(
                        r"https?://[^\s\"']+GetAttachedInvoiceById[^\s\"']+", x
                    )
                    if m:
                        api_urls.append(m.group(0))
                        note(f"api_from_console:{m.group(0)}")
            except Exception as e:
                note(f"console_handler_err:{e}")

        def on_request(req):
            try:
                u = req.url or ""
                if "GetAttachedInvoiceById" in u:
                    api_urls.append(u)
                    note(f"api_req:{u}")
            except Exception:
                pass

        def on_response(resp):
            try:
                u = resp.url or ""
                if "GetAttachedInvoiceById" in u:
                    api_urls.append(u)
                    note(f"api_resp:{u}")
            except Exception:
                pass

        def on_pageerror(err):
            note(f"pageerror:{err}")

        page = context.new_page()
        page.on("console", on_console)
        context.on("request", on_request)
        context.on("response", on_response)
        page.on("pageerror", on_pageerror)

        def safe_shot(suffix: str):
            if not take_screens:
                return
            try:
                page.screenshot(
                    path=os.path.join(screens_dir, f"bezeq_{now_stamp()}_{suffix}.png"),
                    full_page=True,
                )
            except Exception:
                pass

        page.goto(normalized_url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except PWTimeout:
            note("networkidle_timeout")
        safe_shot("before")

        # הורדה ישירה מה-API: פונקציה פנימית
        def direct_api(u: str) -> Optional[str]:
            try:
                resp = context.request.get(
                    u,
                    headers={
                        "Referer": normalized_url,
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/127.0.0.0 Safari/537.36"
                        ),
                    },
                )
                body = resp.body()
                ct = (resp.headers.get("content-type") or "").lower()
                if (ct and "pdf" in ct) or body[:4] == b"%PDF":
                    name = "bezeq_invoice_api.pdf"
                    cd = resp.headers.get("content-disposition") or ""
                    m = re.search(
                        r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, flags=re.I
                    )
                    if m:
                        name = sanitize_filename(m.group(1))
                        if not name.lower().endswith(".pdf"):
                            name += ".pdf"
                    out_path = os.path.join(out_dir, name)
                    with open(out_path, "wb") as f:
                        f.write(body)
                    note(f"saved_from_api:{out_path}")
                    return out_path
                else:
                    note(f"api_resp_not_pdf ct={ct} len={len(body)}")
            except Exception as e:
                note(f"direct_api_err:{e}")
            return None

        # אם כבר נתפס URL—ננסה מיד
        if api_urls:
            for api_u in list(dict.fromkeys(api_urls)):
                pth = direct_api(api_u)
                if pth:
                    res["ok"] = True
                    res["path"] = pth
                    break

        # אם עדיין לא, ננסה "להפעיל" את הדף (לגרום ל-API לצאת)
        if not res["ok"]:
            # נסה ללחוץ על כיתוב "להורדה" / "לצפייה", או aria-label, או semantics
            tried = False
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
                    tried = True
                    break
                except Exception:
                    continue
            if not tried:
                # ניסיון באמצעות flt-semantics
                try:
                    page.evaluate("""() => {
                      const cands = Array.from(document.querySelectorAll('[aria-label]'));
                      for (const el of cands) {
                        const lbl = (el.getAttribute('aria-label') || '').trim();
                        if (lbl.includes('הורדה') || lbl.includes('לצפייה') || lbl.includes('לצפיה')) {
                          el.click(); return true;
                        }
                      }
                      return false;
                    }""")
                except Exception:
                    pass

            time.sleep(1.5)
            if api_urls:
                for api_u in list(dict.fromkeys(api_urls)):
                    pth = direct_api(api_u)
                    if pth:
                        res["ok"] = True
                        res["path"] = pth
                        break

        safe_shot("after")
        if keep_trace:
            try:
                context.tracing.stop(
                    path=os.path.join(out_dir, f"bezeq_trace_{now_stamp()}.zip")
                )
                note("trace_saved")
            except Exception as e:
                note(f"trace_stop_failed:{e}")

        context.close()
        browser.close()
    return res


# ==========================
# לוגיקת זרימה מלאה
# ==========================
TRUSTED_PROVIDERS = [
    # ספקים/דומיינים שמוערכים: ירידה קלה בסף אימות (אם תרצה)
    "myinvoice.bezeq.co.il",
    "my.bezeq.co.il",
    "bmy.bezeq.co.il",
    "icount.co.il",
    "greeninvoice.co.il",
    "ezcount.co.il",
    "tax.gov.il",
    "gov.il",
    "quickbooks.intuit.com",
    "stripe.com",
]

KEYWORD_SUBJECT_HE = r"(חשבונית|קבלה|ארנונה|שובר\s*תשלום|דריש(ת|ה)\s*תשלום)"
KEYWORD_SUBJECT_EN = r"(invoice|receipt|statement|bill)"


def is_invoice_candidate(subj: str, body_preview: str) -> bool:
    s = (subj or "") + " " + (body_preview or "")
    s_l = s.lower()
    if re.search(KEYWORD_SUBJECT_HE, s):
        return True
    if re.search(KEYWORD_SUBJECT_EN, s_l):
        return True
    return False


def main():
    ap = argparse.ArgumentParser(
        description="Graph Invoice Finder (v3.9) + Bezeq API-sniff downloader"
    )

    # Graph
    ap.add_argument("--client-id", required=True)
    ap.add_argument(
        "--authority", default="consumers", help="consumers|organizations|<tenant-id>"
    )
    ap.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ap.add_argument(
        "--end-date", required=True, help="YYYY-MM-DD (exclusive, חותך בחצות)"
    )

    # פלט/תיקיות
    ap.add_argument("--invoices-dir", default="./invoices_out")
    ap.add_argument("--keep-quarantine", action="store_true")
    ap.add_argument("--download-report", default="download_report.json")
    ap.add_argument("--save-json", default=None)
    ap.add_argument("--save-csv", default=None)

    # אימות PDF
    ap.add_argument(
        "--verify", action="store_true", help="אימות PDF עם PyMuPDF (מילות מפתח)"
    )

    # Playwright (רלוונטי ללינקי בזק)
    ap.add_argument("--bezeq-headful", action="store_true")
    ap.add_argument("--bezeq-trace", action="store_true")
    ap.add_argument("--bezeq-screenshots", action="store_true")

    # כללי
    ap.add_argument("--debug", action="store_true")

    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO, format="%(message)s"
    )

    # הכנת תיקיות
    inv_dir = ensure_dir(args.invoices_dir)
    quarant_dir = (
        ensure_dir(os.path.join(inv_dir, "quarantine"))
        if args.keep_quarantine
        else None
    )

    # טווחי תאריכים ל-Graph
    try:
        start_dt = dt.datetime.strptime(args.start_date, "%Y-%m-%d").replace(
            tzinfo=dt.timezone.utc
        )
        end_dt = dt.datetime.strptime(args.end_date, "%Y-%m-%d").replace(
            tzinfo=dt.timezone.utc
        )
    except ValueError:
        print("פורמט תאריך שגוי. השתמשו ב-YYYY-MM-DD")
        sys.exit(3)
    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()

    # התחברות ל-Graph
    gc = GraphClient(client_id=args.client_id, authority=args.authority)

    saved_rows = []  # שורות "הודעה -> נשמר PDF"
    rejected_rows = []  # שורות שנדחו + סיבה
    download_report = []  # רישום מפורט של כל הורדה/ניסיון

    # === לולאת הודעות ===
    count = 0
    for msg in gc.iter_messages(start_iso, end_iso, max_pages=50, page_size=50):
        count += 1
        msg_id = msg.get("id")
        subject = msg.get("subject") or ""
        from_addr = ((msg.get("from") or {}).get("emailAddress") or {}).get(
            "address"
        ) or ""
        received = msg.get("receivedDateTime")
        has_attachments = bool(msg.get("hasAttachments"))
        web_link = msg.get("webLink")
        preview = msg.get("bodyPreview") or ""

        # סינון ראשוני לפי מילות מפתח בנושא/תקציר
        if not (has_attachments or is_invoice_candidate(subject, preview)):
            continue  # חסכון

        logging.info(f"[{count}] {subject} | {from_addr} | {received}")

        # ====== A) קבצים מצורפים ======
        atts = []
        if has_attachments:
            try:
                atts = gc.list_attachments(msg_id)
            except Exception as e:
                rejected_rows.append(
                    {
                        "id": msg_id,
                        "subject": subject,
                        "reason": f"attachments_list_fail:{e}",
                    }
                )

        # הורדת PDF מצורף
        any_saved = False
        for a in atts:
            ct = (a.get("contentType") or "").lower()
            name = a.get("name") or "file"
            if "pdf" not in ct and not name.lower().endswith(".pdf"):
                continue
            try:
                blob = gc.download_attachment(msg_id, a["id"])
                out_name = sanitize_filename(
                    name if name.lower().endswith(".pdf") else name + ".pdf"
                )
                out_path = os.path.join(inv_dir, out_name)
                with open(out_path, "wb") as f:
                    f.write(blob)
                ok = True
                if args.verify:
                    ok = verify_pdf_text(out_path)
                    if not ok:
                        if quarant_dir:
                            qpath = os.path.join(quarant_dir, out_name)
                            os.replace(out_path, qpath)
                            out_path = qpath
                download_report.append(
                    {
                        "msg_id": msg_id,
                        "type": "attachment",
                        "name": name,
                        "path": out_path,
                        "ok": ok,
                    }
                )
                if ok:
                    saved_rows.append(
                        {
                            "id": msg_id,
                            "subject": subject,
                            "from": from_addr,
                            "receivedDateTime": received,
                            "source": "attachment",
                            "path": out_path,
                            "webLink": web_link,
                        }
                    )
                    any_saved = True
            except Exception as e:
                download_report.append(
                    {
                        "msg_id": msg_id,
                        "type": "attachment",
                        "name": name,
                        "reject": f"attach_download_fail:{e}",
                    }
                )

        # ====== B) לינקים מתוך גוף המייל ======
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
                # 1) הורדה ישירה אם PDF
                dpath = download_direct_pdf(
                    u, inv_dir, referer=web_link, ua="Mozilla/5.0"
                )
                if dpath:
                    ok = True
                    if args.verify:
                        ok = verify_pdf_text(dpath)
                        if not ok and quarant_dir:
                            qpath = os.path.join(quarant_dir, os.path.basename(dpath))
                            os.replace(dpath, qpath)
                            dpath = qpath
                    download_report.append(
                        {
                            "msg_id": msg_id,
                            "type": "link",
                            "url": u,
                            "path": dpath,
                            "ok": ok,
                        }
                    )
                    if ok:
                        saved_rows.append(
                            {
                                "id": msg_id,
                                "subject": subject,
                                "from": from_addr,
                                "receivedDateTime": received,
                                "source": "link_direct_pdf",
                                "path": dpath,
                                "webLink": web_link,
                            }
                        )
                        any_saved = True
                        break  # מספיק אחד

                # 2) ספקים ספציפיים – בזק
                if within_domain(
                    u, ["myinvoice.bezeq.co.il", "my.bezeq.co.il", "bmy.bezeq.co.il"]
                ):
                    out = bezeq_fetch_with_api_sniff(
                        url=u,
                        out_dir=inv_dir,
                        headless=not args.bezeq_headful,
                        keep_trace=args.bezeq_trace,
                        take_screens=args.bezeq_screenshots,
                        verbose=args.debug,
                    )
                    if out.get("ok") and out.get("path"):
                        dpath = out["path"]
                        ok = True
                        if args.verify:
                            ok = verify_pdf_text(dpath)
                            if not ok and quarant_dir:
                                qpath = os.path.join(
                                    quarant_dir, os.path.basename(dpath)
                                )
                                os.replace(dpath, qpath)
                                dpath = qpath
                        download_report.append(
                            {
                                "msg_id": msg_id,
                                "type": "link",
                                "url": u,
                                "path": dpath,
                                "ok": ok,
                                "notes": out.get("notes", []),
                            }
                        )
                        if ok:
                            saved_rows.append(
                                {
                                    "id": msg_id,
                                    "subject": subject,
                                    "from": from_addr,
                                    "receivedDateTime": received,
                                    "source": "bezeq_api",
                                    "path": dpath,
                                    "webLink": web_link,
                                }
                            )
                            any_saved = True
                            break
                    else:
                        download_report.append(
                            {
                                "msg_id": msg_id,
                                "type": "link",
                                "url": u,
                                "reject": "bezeq_fetch_failed",
                                "notes": out.get("notes", []),
                            }
                        )

            if not any_saved and links:
                # לא הצלחנו עם אף לינק
                rejected_rows.append(
                    {"id": msg_id, "subject": subject, "reason": "links_no_pdf"}
                )

        # אם גם קבצים וגם לינקים לא הצליחו – נרשום דחייה
        if not any_saved and not has_attachments:
            rejected_rows.append(
                {"id": msg_id, "subject": subject, "reason": "no_attach_no_pdf_links"}
            )

    # ====== כתיבת דוחות ======
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
        fieldnames = [
            "id",
            "subject",
            "from",
            "receivedDateTime",
            "source",
            "path",
            "webLink",
        ]
        with open(args.save_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            [w.writerow({k: r.get(k) for k in fieldnames}) for r in saved_rows]
        print(f"Saved messages CSV → {args.save_csv}")

    print(
        f"Done. Found & saved {len(saved_rows)} invoices. Rejected {len(rejected_rows)}."
    )


if __name__ == "__main__":
    main()
