#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bezeq_invoice_fetcher_v3_8_6.py

מטרה
------
להוריד חשבונית PDF מקישור המייל של בזק (myinvoice.bezeq.co.il), SPA של Flutter.
הסקריפט:
  • מנרמל URL-ים בעייתיים (מסיר '\?' '\&' '\\=' ומתקן '//?' -> '/?').
  • מתמודד עם Canvas/Flutter (flt-semantics + קליק בקואורדינטות).
  • לוכד הורדות blob/new-tab.
  • מזהה PDF גם אם content-type הוא application/octet-stream עם Content-Disposition.
  • תומך בצופה PDF.js (לחיצה על כפתור ההורדה של הצופה).

תלויות
------
    pip install playwright
    playwright install

דוגמאות הרצה
-------------
# מצב דיבוג: חלון גלוי + trace + צילומי מסך + לוג
python bezeq_invoice_fetcher_v3_8_6.py \
  --url "https://myinvoice.bezeq.co.il/?MailID=..." \
  --out-dir "./invoices_out_bezeq" \
  --headful --trace --screenshots --verbose

# מצב ברירת מחדל: headless + trace + screenshots
python bezeq_invoice_fetcher_v3_8_6.py \
  --url "https://myinvoice.bezeq.co.il/?MailID=..." \
  --out-dir "./invoices_out_bezeq"

מה חדש בגרסה זו (v3.8.6)
-------------------------
1) normalize_myinvoice_url(): מסיר backslashes מ־querystring ומתקן '//' לפני '?'.
2) אזהרה/הערה אם נתקלנו ב־SecurityError של replaceState (רמז ל־URL פגום).
3) שומר את ה־original_url וגם normalized_url בשדה notes.
4) כל שאר התיקונים מ־3.8.5 נשמרו (מאזיני console/version-safe, זמן UTC מודע, semantics click, לכידת PDF וכו').

פלט
----
JSON עם שדות: {"ok": bool, "path": str|None, "url": str, "out_dir": str, "notes": [...]}
קוד יציאה: 0 אם הצלחה, 2 אם לא נשמר PDF.
"""

import os
import re
import sys
import json
import time
import pathlib
import argparse
from typing import Optional, List, Tuple
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

HE_UNICODE_DL = r"\u05DC\u05D4\u05D5\u05E8\u05D3\u05D4"  # "להורדה"
HE_UNICODE_VIEW = r"\u05DC\u05E6\u05E4\u05D9\u05D4"  # "לצפיה"


# ---------- עזרי קבצים/זמן ----------


def sanitize_filename(name: str, default: str = "invoice.pdf") -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "_", (name or "").strip())
    return name or default


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def ensure_dir(p: str) -> str:
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)
    return p


# ---------- נרמול URL של myinvoice ----------


def normalize_myinvoice_url(u: str) -> str:
    """
    מתקנת קלטים כמו:
      https://myinvoice.bezeq.co.il/\\?MailID\\=...\\&utm_source\\=...
      https://myinvoice.bezeq.co.il//?MailID=...

    החוקים:
      - הסרת backslashes לפני ?, &, =.
      - צמצום '//' אחרי הדומיין ל־'/' (לפני '?').
    """
    s = (u or "").strip()

    # הסרת בריחות shell נפוצות
    s = s.replace("\\?", "?").replace("\\&", "&").replace("\\=", "=")

    # אם נשאר לנו '//?' אחרי הדומיין – לתקן ל'/?'
    # נקודתי לדומיין myinvoice; לא פוגע ב-'https://'
    s = s.replace("://myinvoice.bezeq.co.il//?", "://myinvoice.bezeq.co.il/?")

    # fallback עדין: אם אחרי הדומיין יש יותר מסלאש אחד ומיד '?', כווץ לאחד.
    s = re.sub(r"(://myinvoice\.bezeq\.co\.il)/+(?=\?)", r"\1/", s)

    return s


# ---------- צילום מסך בטוח ----------


def safe_screenshot(
    page, path: str, *, full_page: bool = True, notes: Optional[list] = None
) -> bool:
    def log(msg: str):
        if isinstance(notes, list):
            notes.append(msg)

    try:
        ss = getattr(page, "screenshot", None)
        if callable(ss):
            ss(path=path, full_page=full_page)
            log(f"screenshot: page -> {path}")
            return True
        else:
            log("screenshot attr not callable; fallback")
    except Exception as e:
        log(f"screenshot primary failed: {type(e).__name__}: {e}")
    for sel in ("html", "body"):
        try:
            page.locator(sel).screenshot(path=path)
            log(f"screenshot: locator('{sel}') -> {path}")
            return True
        except Exception as e:
            log(f"screenshot {sel} failed: {type(e).__name__}: {e}")
    return False


# ---------- עזרי DOM/לחיצה ----------


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
        pattern = re.sub(r"([().\[\]^$*+?{}|\\])", r"\\\1", t)
        if visible_then_click(page, f"text=/{pattern}/", timeout_ms):
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
        if data and isinstance(data, list):
            data.sort(key=lambda d: (0 if "הורד" in d["label"] else 1))
            x, y = float(data[0]["x"]), float(data[0]["y"])
            page.mouse.click(x, y, delay=30)
            return True, (x, y)
        return False, None
    except Exception:
        return False, None


# ---------- לכידת תגובות PDF ----------


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


# ---------- מאזינים אחידים ----------


def _maybe_call(x):
    try:
        return x() if callable(x) else x
    except Exception:
        return x


def attach_page_listeners(page, *, downloads_bucket: list, note):
    def on_download(d):
        downloads_bucket.append(d)
        try:
            suggested = getattr(d, "suggested_filename", None)
        except Exception:
            suggested = None
        note(f"download event: suggested={suggested}")

    def on_console(msg):
        try:
            msg_type = _maybe_call(getattr(msg, "type", ""))
            msg_text = _maybe_call(getattr(msg, "text", ""))
            note(f"console:{msg_type}:{msg_text}")
            # רמז ל-URL פגום (כפי שנצפה בלוג שלך)
            if "SecurityError" in str(msg_text) and "replaceState" in str(msg_text):
                note("hint:url_malformed_replaceState_securityerror")
        except Exception as ex:
            note(f"console_handler_error:{ex}")

    def on_pageerror(err):
        try:
            note(f"pageerror:{err}")
        except Exception as ex:
            note(f"pageerror_handler_error:{ex}")

    page.on("download", on_download)
    page.on("console", on_console)
    page.on("pageerror", on_pageerror)


# ---------- הלוגיקה הראשית ----------


def fetch_bezeq_pdf(
    url: str,
    out_dir: str,
    timeout: int = 45,
    headless: bool = True,
    take_screens: bool = True,
    keep_trace: bool = True,
    verbose: bool = False,
) -> dict:
    ensure_dir(out_dir)
    run = {"url": url, "out_dir": out_dir, "ok": False, "path": None, "notes": []}

    def note(msg: str):
        if verbose:
            print(msg)
        run["notes"].append(msg)

    normalized_url = normalize_myinvoice_url(url)
    if normalized_url != url:
        note(f"url_normalized_from:{url}")
        note(f"url_normalized_to:{normalized_url}")

    screenshots_dir = os.path.join(out_dir, "screens")
    if take_screens:
        ensure_dir(screenshots_dir)

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
            ignore_https_errors=False,
            java_script_enabled=True,
            color_scheme="light",
        )

        if keep_trace:
            context.tracing.start(screenshots=True, snapshots=True, sources=False)

        pdf_responses: List = []

        def sniff_response(resp):
            if is_pdf_like_response(resp):
                pdf_responses.append(resp)
                note(f"pdf-like response: {resp.url}")

        context.on("response", sniff_response)

        downloads: List = []

        def on_new_page(p):
            attach_page_listeners(p, downloads_bucket=downloads, note=note)

        context.on("page", on_new_page)

        page = context.new_page()
        attach_page_listeners(page, downloads_bucket=downloads, note=note)
        page.set_default_timeout(timeout * 1000)

        # ניווט
        page.goto(normalized_url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except PWTimeout:
            note("networkidle_timeout")

        if take_screens:
            p_before = os.path.join(screenshots_dir, f"bezeq_{now_stamp()}_before.png")
            safe_screenshot(page, p_before, full_page=True, notes=run["notes"])

        # --- נסיונות לחיצה על “להורדה / לצפיה” ---
        clicked = (
            try_click_by_texts(page, ["להורדה", "לצפייה", "לצפיה"])
            or visible_then_click(page, '[aria-label*="הורדה"],[title*="הורדה"]')
            or try_click_by_texts(page, [HE_UNICODE_DL, HE_UNICODE_VIEW])
            or scan_dom_for_hebrew_and_click(page, r"(להורד[הא]|לצפ(י|י)ה)")
        )
        if not clicked:
            clicked, xy = click_by_semantics_label(page, ["הורדה", "לצפייה", "לצפיה"])
            if clicked:
                note(f"clicked via semantics at {xy}")

        if not clicked:
            page.mouse.wheel(0, 1200)
            time.sleep(0.4)
            clicked = (
                try_click_by_texts(page, ["להורדה", "לצפייה", "לצפיה"])
                or visible_then_click(page, '[aria-label*="הורדה"],[title*="הורדה"]')
                or scan_dom_for_hebrew_and_click(page, r"(להורד[הא]|לצפ(י|י)ה)")
                or click_by_semantics_label(page, ["הורדה", "לצפייה", "לצפיה"])[0]
            )

        note("clicked_download_or_view" if clicked else "click_failed")
        time.sleep(1.0)

        # --- הורדות/תגובות ---
        if not run["ok"] and downloads:
            try:
                d = downloads[-1]
                suggested = (
                    getattr(d, "suggested_filename", None) or "bezeq_invoice.pdf"
                )
                out_path = os.path.join(out_dir, sanitize_filename(suggested))
                d.save_as(out_path)
                run.update(ok=True, path=out_path)
                note(f"saved from download event -> {out_path}")
            except Exception as e:
                note(f"download save failed: {e}")

        if not run["ok"] and pdf_responses:
            resp = pdf_responses[-1]
            try:
                body = resp.body()
                name = "bezeq_invoice_resp.pdf"
                cd = resp.headers().get("content-disposition") or ""
                m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, flags=re.I)
                if m:
                    name = sanitize_filename(m.group(1))
                    if not name.lower().endswith(".pdf"):
                        name += ".pdf"
                out_path = os.path.join(out_dir, sanitize_filename(name))
                with open(out_path, "wb") as f:
                    f.write(body)
                run.update(ok=True, path=out_path)
                note(f"saved from response -> {out_path}")
            except Exception as e:
                note(f"response save failed: {e}")

        if not run["ok"]:
            if visible_then_click(
                page,
                '[title*="Download"], [aria-label*="Download"], [aria-label*="הורדה"]',
                3000,
            ):
                time.sleep(0.8)
                if downloads:
                    try:
                        d = downloads[-1]
                        suggested = (
                            getattr(d, "suggested_filename", None)
                            or "bezeq_invoice_pdfjs.pdf"
                        )
                        out_path = os.path.join(out_dir, sanitize_filename(suggested))
                        d.save_as(out_path)
                        run.update(ok=True, path=out_path)
                        note(f"saved via pdfjs download -> {out_path}")
                    except Exception as e:
                        note(f"pdfjs download save failed: {e}")
                if not run["ok"] and pdf_responses:
                    try:
                        resp = pdf_responses[-1]
                        out_path = os.path.join(out_dir, "bezeq_invoice_pdfjs_resp.pdf")
                        with open(out_path, "wb") as f:
                            f.write(resp.body())
                        run.update(ok=True, path=out_path)
                        note(f"saved via pdfjs response -> {out_path}")
                    except Exception as e:
                        note(f"pdfjs response save failed: {e}")

        # --- צילומי מסך/trace ---
        if take_screens:
            p_after = os.path.join(screenshots_dir, f"bezeq_{now_stamp()}_after.png")
            safe_screenshot(page, p_after, full_page=True, notes=run["notes"])

        if keep_trace:
            trace_path = os.path.join(out_dir, f"bezeq_trace_{now_stamp()}.zip")
            try:
                context.tracing.stop(path=trace_path)
                note(f"trace:{trace_path}")
            except Exception as e:
                note(f"trace_stop_failed:{e}")

        context.close()
        browser.close()

    return run


# ---------- CLI ----------


def main():
    ap = argparse.ArgumentParser(
        description="Bezeq (myinvoice) PDF fetcher – Flutter/Blob/PDF.js aware (v3.8.6)"
    )
    ap.add_argument(
        "--url",
        required=True,
        help="קישור המייל של בזק (myinvoice.bezeq.co.il/?MailID=...)",
    )
    ap.add_argument("--out-dir", default="./invoices_out", help="תיקיית יעד לקבצים")
    ap.add_argument(
        "--timeout", type=int, default=45, help="טיימאאוט כולל לעמוד (שניות)"
    )

    g_head = ap.add_mutually_exclusive_group()
    g_head.add_argument(
        "--headful", dest="headful", action="store_true", help="פתח דפדפן עם UI"
    )
    g_head.add_argument(
        "--headless",
        dest="headful",
        action="store_false",
        help="דפדפן ללא UI (בררת מחדל)",
    )
    ap.set_defaults(headful=False)

    g_trace = ap.add_mutually_exclusive_group()
    g_trace.add_argument(
        "--trace",
        dest="trace",
        action="store_true",
        help="הפעל playwright trace (בררת מחדל)",
    )
    g_trace.add_argument(
        "--no-trace", dest="trace", action="store_false", help="כבה trace"
    )
    ap.set_defaults(trace=True)

    g_ss = ap.add_mutually_exclusive_group()
    g_ss.add_argument(
        "--screenshots",
        dest="screenshots",
        action="store_true",
        help="שמור צילומי מסך (בררת מחדל)",
    )
    g_ss.add_argument(
        "--no-screenshots",
        dest="screenshots",
        action="store_false",
        help="אל תשמור צילומי מסך",
    )
    ap.set_defaults(screenshots=True)

    ap.add_argument("--verbose", action="store_true", help="לוג קצר למסוף בזמן ריצה")

    args = ap.parse_args()

    out_dir = ensure_dir(args.out_dir)
    res = fetch_bezeq_pdf(
        url=args.url,
        out_dir=out_dir,
        timeout=args.timeout,
        headless=(not args.headful),
        take_screens=args.screenshots,
        keep_trace=args.trace,
        verbose=args.verbose,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if not res["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
