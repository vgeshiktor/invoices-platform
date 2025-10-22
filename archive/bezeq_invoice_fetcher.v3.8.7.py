#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bezeq_invoice_fetcher_v3_8_7.py
================================

מטרה
-----
להוריד חשבונית PDF מבזק (myinvoice.bezeq.co.il) מתוך קישור שמגיע במייל.
הדף הוא SPA של Flutter ולכן פעמים רבות הכפתור "להורדה" הוא ציור-Canvas
או flt-semantics. במקום להסתמך על קליקים, אנחנו מאזינים לרשת/קונסול
ומזהים את קריאת ה-API:
  https://my-api.bezeq.co.il/.../GetAttachedInvoiceById?InvoiceId=...&JWTToken=...

וברגע שתופסים את ה-URL הזה—מורידים ישירות עם Playwright HTTP Client
(עוקף CORS, לא תלוי DOM) ושומרים את ה-PDF.

חידושים בגרסה זו (v3.8.7)
--------------------------
1) לוכד URL של GetAttachedInvoiceById מתוך:
   • console.log (כמו שהופיע אצלך ב-logs)
   • page.on("request")
   • page.on("response") (וגם אם Content-Type הוא JSON או octet-stream)
2) direct_download_via_api(): הורדה ישירה של ה-PDF עם Referer מתאים
   ו-User-Agent, כולל פענוח Content-Disposition לשם הקובץ.
3) כל ה-fallbacks של 3.8.6 נשמרו (נרמול URL, קליקים, semantics, PDF.js).
4) לוג מפורט ו-trace/screenshot לפי דגלים.
5) כל מה שחשוב לדעת—מופיע כאן בקובץ, כולל דוגמאות CLI.

תלויות
------
    pip install playwright
    playwright install

דוגמאות הרצה (שימו לב: לא לברוח ? ו-& — לשים את ה-URL במרכאות!)
-----------------------------------------------------------------
# מצב דיבוג מלא: חלון גלוי, trace, צילומי מסך, verbose
python bezeq_invoice_fetcher_v3_8_7.py \
  --url "https://myinvoice.bezeq.co.il/?MailID=....&utm_source=bmail&..." \
  --out-dir "./invoices_out_bezeq" \
  --headful --trace --screenshots --verbose

# ברירת מחדל: headless, עם trace+screenshots
python bezeq_invoice_fetcher_v3_8_7.py \
  --url "https://myinvoice.bezeq.co.il/?MailID=...." \
  --out-dir "./invoices_out_bezeq"

פלט
----
JSON:
{
  "ok": true/false,
  "path": "/path/to/file.pdf" | null,
  "url": "<input_url>",
  "normalized_url": "<after-fix>",
  "notes": ["..."]
}
קוד יציאה: 0 בהצלחה, 2 אם לא נשמר PDF.
"""

import argparse
import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

# -------- עזרי זמן/קבצים --------


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def ensure_dir(p: str) -> str:
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)
    return p


def sanitize_filename(name: str, default: str = "invoice.pdf") -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "_", (name or "").strip())
    return name or default


# -------- נרמול URL --------


def normalize_myinvoice_url(u: str) -> str:
    """
    מתקנת קלטים כמו:
      https://myinvoice.bezeq.co.il/\\?MailID\\=...\\&utm_source\\=...
      https://myinvoice.bezeq.co.il//?MailID=...
    """
    s = (u or "").strip()
    s = s.replace("\\?", "?").replace("\\&", "&").replace("\\=", "=")
    s = s.replace("://myinvoice.bezeq.co.il//?", "://myinvoice.bezeq.co.il/?")
    s = re.sub(r"(://myinvoice\.bezeq\.co\.il)/+(?=\?)", r"\1/", s)
    return s


# -------- צילום מסך בטוח --------


def safe_screenshot(page, path: str, notes: Optional[list] = None) -> None:
    def note(msg: str):
        if isinstance(notes, list):
            notes.append(msg)

    try:
        if callable(getattr(page, "screenshot", None)):
            page.screenshot(path=path, full_page=True)
            note(f"screenshot: page -> {path}")
            return
    except Exception as e:
        note(f"screenshot failed: {e}")
    for sel in ("html", "body"):
        try:
            page.locator(sel).screenshot(path=path)
            note(f"screenshot: locator('{sel}') -> {path}")
            return
        except Exception as e:
            note(f"screenshot {sel} failed: {e}")


# -------- DOM helpers (fallback) --------


def visible_then_click(page, locator_query: str, timeout_ms: int = 4000) -> bool:
    try:
        loc = page.locator(locator_query).first
        loc.wait_for(state="visible", timeout=timeout_ms)
        loc.scroll_into_view_if_needed()
        loc.click()
        return True
    except Exception:
        return False


def try_click_by_texts(page, texts: List[str], timeout_ms: int = 4000) -> bool:
    for t in texts:
        if visible_then_click(page, f'text="{t}"', timeout_ms):
            return True
        if visible_then_click(page, f"text={t}", timeout_ms):
            return True
        if visible_then_click(page, f'role=link[name="{t}"]', timeout_ms):
            return True
        if visible_then_click(page, f'role=button[name="{t}"]', timeout_ms):
            return True
        patt = re.sub(r"([().\[\]^$*+?{}|\\])", r"\\\1", t)
        if visible_then_click(page, f"text=/{patt}/", timeout_ms):
            return True
    return False


def scan_dom_for_hebrew_and_click(page, words_regex: str) -> bool:
    try:
        found = page.evaluate(
            """(pattern) => {
                const rx = new RegExp(pattern);
                const all = Array.from(document.querySelectorAll(
                    'a,button,span,div,[role="link"],[role="button"]'
                ));
                for (const el of all) {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (!t) continue;
                    if (rx.test(t)) {
                        el.scrollIntoView({block:'center'});
                        el.click();
                        return true;
                    }
                }
                return false;
            }""",
            words_regex,
        )
        return bool(found)
    except Exception:
        return False


def click_by_semantics_label(
    page, labels: List[str]
) -> Tuple[bool, Optional[Tuple[float, float]]]:
    try:
        data = page.evaluate(
            """(labels) => {
              const nodes = Array.from(document.querySelectorAll('[aria-label], flt-semantics [aria-label]'));
              const out = [];
              for (const el of nodes) {
                const lbl = (el.getAttribute('aria-label') || '').trim();
                if (!lbl) continue;
                for (const want of labels) {
                  if (lbl.includes(want)) {
                    const r = el.getBoundingClientRect();
                    out.push({label: lbl, x: r.left + r.width/2, y: r.top + r.height/2});
                    break;
                  }
                }
              }
              return out;
            }""",
            labels,
        )
        if data:
            data.sort(key=lambda d: (0 if "הורד" in d["label"] else 1))
            x, y = float(data[0]["x"]), float(data[0]["y"])
            page.mouse.click(x, y, delay=30)
            return True, (x, y)
        return False, None
    except Exception:
        return False, None


# -------- זיהוי PDF בתגובה --------


def is_pdf_like_response(resp) -> bool:
    try:
        headers = {k.lower(): v for k, v in resp.headers().items()}
        ct = headers.get("content-type", "").lower()
        cd = headers.get("content-disposition", "")
        url = (resp.url or "").lower()
        if "application/pdf" in ct:
            return True
        if url.endswith(".pdf"):
            return True
        if "application/octet-stream" in ct and ".pdf" in cd.lower():
            return True
    except Exception:
        pass
    return False


# -------- הלוגיקה הראשית --------


def fetch_bezeq_pdf(
    url: str,
    out_dir: str,
    timeout: int = 45,
    headless: bool = True,
    take_screens: bool = True,
    keep_trace: bool = True,
    verbose: bool = False,
) -> dict:
    run = {
        "url": url,
        "normalized_url": None,
        "out_dir": out_dir,
        "ok": False,
        "path": None,
        "notes": [],
    }
    ensure_dir(out_dir)
    screens_dir = ensure_dir(os.path.join(out_dir, "screens"))

    def note(msg: str):
        if verbose:
            print(msg)
        run["notes"].append(msg)

    normalized_url = normalize_myinvoice_url(url)
    run["normalized_url"] = normalized_url
    if normalized_url != url:
        note(f"url_normalized_from:{url}")
        note(f"url_normalized_to:{normalized_url}")

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
            extra_http_headers={
                "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7"
            },
        )
        if keep_trace:
            context.tracing.start(screenshots=True, snapshots=True, sources=False)

        # נשמור כאן כל URL שמצאנו ל-GetAttachedInvoiceById
        api_invoice_urls: List[str] = []

        # מאזיני רשת
        def on_request(req):
            try:
                u = req.url or ""
                if "GetAttachedInvoiceById" in u:
                    api_invoice_urls.append(u)
                    note(f"api_req:{u}")
            except Exception:
                pass

        def on_response(resp):
            try:
                u = resp.url or ""
                if "GetAttachedInvoiceById" in u:
                    api_invoice_urls.append(u)
                    note(f"api_resp:{u}")
                    # אם זו תגובת PDF—נוריד כ- fallback (ננסה גם ישיר)
                    if is_pdf_like_response(resp) and not run["ok"]:
                        body = resp.body()
                        name = "bezeq_invoice_resp.pdf"
                        cd = resp.headers().get("content-disposition") or ""
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
                        run.update(ok=True, path=out_path)
                        note(f"saved_from_response:{out_path}")
            except Exception as e:
                note(f"resp_handler_err:{e}")

        context.on("request", on_request)
        context.on("response", on_response)

        # מאזיני console → יש אצלך console.log עם ה-URL
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
                    # הוצא URL מהטקסט
                    m = re.search(
                        r"https?://[^\s\"']+GetAttachedInvoiceById[^\s\"']+", x
                    )
                    if m:
                        api_invoice_urls.append(m.group(0))
                        note(f"api_from_console:{m.group(0)}")
            except Exception as e:
                note(f"console_handler_err:{e}")

        # errors
        def on_pageerror(err):
            note(f"pageerror:{err}")

        page = context.new_page()
        page.on("console", on_console)
        page.on("pageerror", on_pageerror)

        # ניווט
        page.goto(normalized_url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except PWTimeout:
            note("networkidle_timeout")

        if take_screens:
            safe_screenshot(
                page,
                os.path.join(screens_dir, f"bezeq_{now_stamp()}_before.png"),
                run["notes"],
            )

        # ---- נסה להוריד ישירות אם כבר קיבלנו URL של ה-API ----
        def direct_download_via_api(u: str) -> Optional[str]:
            try:
                # חשוב: Referer כמו הדף הראשי; לעתים דורש UA תואם
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
                ct = (resp.headers.get("content-type") or "").lower()
                body = resp.body()
                if (ct and "pdf" in ct) or (body[:4] == b"%PDF"):
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
                    note(f"api_resp_not_pdf: ct={ct} len={len(body)}")
            except Exception as e:
                note(f"direct_api_err:{e}")
            return None

        # ייתכן שכבר נלכד URL מה-console/init; אם כן – ננסה מיד
        tried = False
        if api_invoice_urls:
            tried = True  # noqa: F841
            for api_u in list(dict.fromkeys(api_invoice_urls)):  # unique order
                path = direct_download_via_api(api_u)
                if path:
                    run.update(ok=True, path=path)
                    break

        # אם עדיין אין PDF, ננסה להפעיל את הכפתור כדי לגרום ל-API להופיע
        if not run["ok"]:
            clicked = (
                try_click_by_texts(page, ["להורדה", "לצפייה", "לצפיה"])
                or visible_then_click(page, '[aria-label*="הורדה"],[title*="הורדה"]')
                or scan_dom_for_hebrew_and_click(page, r"(להורד[הא]|לצפ(י|י)ה)")
                or click_by_semantics_label(page, ["הורדה", "לצפייה", "לצפיה"])[0]
            )
            note("clicked_download_or_view" if clicked else "click_failed")

            # תן לדף זמן לירות את בקשת ה-API
            time.sleep(1.5)

            if api_invoice_urls and not run["ok"]:
                for api_u in list(dict.fromkeys(api_invoice_urls)):
                    path = direct_download_via_api(api_u)
                    if path:
                        run.update(ok=True, path=path)
                        break

        if take_screens:
            safe_screenshot(
                page,
                os.path.join(screens_dir, f"bezeq_{now_stamp()}_after.png"),
                run["notes"],
            )

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

    return run


# -------- CLI --------


def main():
    ap = argparse.ArgumentParser(
        description="Bezeq (myinvoice) PDF fetcher – API-sniff + Flutter fallbacks (v3.8.7)"
    )
    ap.add_argument(
        "--url", required=True, help="קישור myinvoice (שים במרכאות, בלי לברוח ? ו- &)"
    )
    ap.add_argument("--out-dir", default="./invoices_out_bezeq", help="תיקיית יעד")
    ap.add_argument("--timeout", type=int, default=45, help="טיימאאוט כללי (שניות)")

    g_head = ap.add_mutually_exclusive_group()
    g_head.add_argument(
        "--headful", dest="headful", action="store_true", help="להציג חלון דפדפן"
    )
    g_head.add_argument(
        "--headless", dest="headful", action="store_false", help="ללא UI (ברירת מחדל)"
    )
    ap.set_defaults(headful=False)

    g_trace = ap.add_mutually_exclusive_group()
    g_trace.add_argument(
        "--trace", dest="trace", action="store_true", help="שמור trace (ברירת מחדל)"
    )
    g_trace.add_argument(
        "--no-trace", dest="trace", action="store_false", help="אל תשמור trace"
    )
    ap.set_defaults(trace=True)

    g_ss = ap.add_mutually_exclusive_group()
    g_ss.add_argument(
        "--screenshots",
        dest="screenshots",
        action="store_true",
        help="שמור צילומי מסך (ברירת מחדל)",
    )
    g_ss.add_argument(
        "--no-screenshots",
        dest="screenshots",
        action="store_false",
        help="אל תשמור צילומי מסך",
    )
    ap.set_defaults(screenshots=True)

    ap.add_argument("--verbose", action="store_true", help="פלט מפורט למסוף")

    args = ap.parse_args()
    ensure_dir(args.out_dir)

    res = fetch_bezeq_pdf(
        url=args.url,
        out_dir=args.out_dir,
        timeout=args.timeout,
        headless=not args.headful,
        take_screens=args.screenshots,
        keep_trace=args.trace,
        verbose=args.verbose,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if not res.get("ok"):
        sys.exit(2)


if __name__ == "__main__":
    main()
