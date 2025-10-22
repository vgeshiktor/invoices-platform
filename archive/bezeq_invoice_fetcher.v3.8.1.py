#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bezeq_invoice_fetcher_v38_1.py

תכלית:
- להוריד חשבונית PDF מקישור myinvoice.bezeq.co.il (בזק) שמרנדר Flutter/PDF.js.

איך מריצים:
    python bezeq_invoice_fetcher_v38_1.py \
        --url "https://myinvoice.bezeq.co.il/?MailID=..." \
        --out-dir "./invoices_out" \
        --timeout 45 \
        --headful \
        --trace

התקנות:
    pip install playwright
    playwright install

מה חדש בגרסה 38.1:
- תיקון לקריסת Page.screenshot ("'str' object is not callable"):
  הוספתי safe_screenshot() שמנסה קודם page.screenshot ואם זה נופל — מצלם דרך
  locator("html")/locator("body") בלי full_page. בנוסף, צילום מסך כבר לא מפיל את הריצה.
- שמירה על כל היכולות: הורדה דרך Download Event, זיהוי חלון קופץ, ולכידת Response של PDF.
"""

import os
import re
import sys
import json
import time
import pathlib
import argparse
from typing import Optional, List
from datetime import datetime as dt

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

HE_UNICODE_DL = r"\u05DC\u05D4\u05D5\u05E8\u05D3\u05D4"  # "להורדה"
HE_UNICODE_VIEW = r"\u05DC\u05E6\u05E4\u05D9\u05D4"  # "לצפיה"


def sanitize_filename(name: str, default: str = "invoice.pdf") -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", (name or "").strip())
    return name or default


def now_stamp() -> str:
    return dt.utcnow().strftime("%Y%m%d_%H%M%S")


def ensure_dir(p: str) -> str:
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)
    return p


# -------------------- צילום מסך בטוח --------------------


def safe_screenshot(
    page, path: str, *, full_page: bool = True, notes: Optional[list] = None
) -> bool:
    """
    מצלם מסך בלי להפיל את ההרצה, עם Fallbacks:
    1) page.screenshot(full_page=...)  (אם אפשר)
    2) locator("html").screenshot()
    3) locator("body").screenshot()
    """

    def log(msg: str):
        if isinstance(notes, list):
            notes.append(msg)

    # נסיון 1: ה־API הסטנדרטי
    try:
        ss = getattr(page, "screenshot", None)
        if callable(ss):
            ss(path=path, full_page=full_page)
            log(f"screenshot: ok via page.screenshot -> {path}")
            return True
        else:
            log("screenshot attr not callable; will fallback")
    except Exception as e:
        log(f"screenshot primary failed: {type(e).__name__}: {e}")

    # נסיון 2: דרך ה־DOM
    try:
        page.locator("html").screenshot(path=path)
        log(f"screenshot: ok via locator('html') -> {path}")
        return True
    except Exception as e:
        log(f"screenshot html locator failed: {type(e).__name__}: {e}")

    # נסיון 3: גוף הדף
    try:
        page.locator("body").screenshot(path=path)
        log(f"screenshot: ok via locator('body') -> {path}")
        return True
    except Exception as e:
        log(f"screenshot body locator failed: {type(e).__name__}: {e}")

    return False


# -------------------- עזרי ניווט/הורדה --------------------


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
        # regex
        pattern = re.sub(r"([().\[\]^$*+?{}|\\])", r"\\\1", t)
        if visible_then_click(page, f"text=/{pattern}/", timeout_ms):
            return True
    return False


def scan_dom_for_hebrew_and_click(
    page, words_regex: str, timeout_ms: int = 5000
) -> bool:
    try:
        page.wait_for_timeout(300)
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


def attach_pdf_sniffer(page, bucket: list):
    def on_response(resp):
        try:
            ct = (resp.headers().get("content-type") or "").lower()
            if "application/pdf" in ct or resp.url.lower().endswith(".pdf"):
                bucket.append(resp)
        except Exception:
            pass

    page.on("response", on_response)


def wait_and_save_download(
    page, out_dir: str, base_name: str, timeout_ms: int = 15000
) -> Optional[str]:
    try:
        with page.expect_download(timeout=timeout_ms) as dl_info:
            pass
    except PWTimeout:
        return None
    try:
        download = dl_info.value
        suggested = sanitize_filename(
            download.suggested_filename or (base_name + ".pdf")
        )
        out_path = os.path.join(out_dir, suggested)
        download.save_as(out_path)
        return out_path
    except Exception:
        return None


def save_pdf_from_response(resp, out_dir: str, base_name: str) -> Optional[str]:
    try:
        body = resp.body()
        out_path = os.path.join(out_dir, sanitize_filename(base_name + ".pdf"))
        with open(out_path, "wb") as f:
            f.write(body)
        return out_path
    except Exception:
        return None


# -------------------- הרוטינה הראשית --------------------


def fetch_bezeq_pdf(
    url: str,
    out_dir: str,
    timeout: int = 45,
    headless: bool = False,
    take_screens: bool = True,
    keep_trace: bool = True,
) -> dict:
    """
    נכנס לקישור חשבונית בזק ומנסה להוריד PDF, עם Fallbacks ללחיצה/הורדה.
    """
    ensure_dir(out_dir)
    run = {"url": url, "out_dir": out_dir, "ok": False, "path": None, "notes": []}
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

        page = context.new_page()
        page.on(
            "console", lambda m: run["notes"].append(f"console:{m.type()}:{m.text()}")
        )
        page.on("pageerror", lambda e: run["notes"].append(f"pageerror:{e}"))

        pdf_responses: List = []
        attach_pdf_sniffer(page, pdf_responses)

        page.set_default_timeout(timeout * 1000)
        page.goto(url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except PWTimeout:
            run["notes"].append("networkidle_timeout")

        if take_screens:
            p_before = os.path.join(screenshots_dir, f"bezeq_{now_stamp()}_before.png")
            safe_screenshot(page, p_before, full_page=True, notes=run["notes"])

        # נסיונות לחיצה
        clicked = (
            try_click_by_texts(page, ["להורדה", "לצפייה", "לצפיה"])
            or visible_then_click(page, '[aria-label*="הורדה"],[title*="הורדה"]')
            or try_click_by_texts(page, [HE_UNICODE_DL, HE_UNICODE_VIEW])
            or scan_dom_for_hebrew_and_click(page, r"(להורד[הא]|לצפ(י|י)ה)")
        )
        if not clicked:
            page.mouse.wheel(0, 1200)
            time.sleep(0.4)
            clicked = (
                try_click_by_texts(page, ["להורדה", "לצפייה", "לצפיה"])
                or visible_then_click(page, '[aria-label*="הורדה"],[title*="הורדה"]')
                or scan_dom_for_hebrew_and_click(page, r"(להורד[הא]|לצפ(י|י)ה)")
            )

        run["notes"].append("clicked_download_or_view" if clicked else "click_failed")

        # 1) נסיון ללכוד Download Event
        saved = wait_and_save_download(
            page, out_dir, base_name="bezeq_invoice", timeout_ms=15000
        )
        if saved:
            run.update(ok=True, path=saved)
        else:
            # 2) אולי נפתח חלון חדש
            try:
                with context.expect_page(timeout=5000) as pop_ev:
                    pass
                newp = pop_ev.value
                attach_pdf_sniffer(newp, pdf_responses)
                saved2 = wait_and_save_download(
                    newp, out_dir, base_name="bezeq_invoice_popup", timeout_ms=15000
                )
                if saved2:
                    run.update(ok=True, path=saved2)
                else:
                    time.sleep(1500 / 1000)
            except PWTimeout:
                pass

        # 3) נסיון מלכוד תגובות PDF
        if not run["ok"] and pdf_responses:
            resp = pdf_responses[-1]
            saved3 = save_pdf_from_response(
                resp, out_dir, base_name="bezeq_invoice_resp"
            )
            if saved3:
                run.update(ok=True, path=saved3)

        # 4) אם מדובר ב־PDF.js: לנסות כפתור ההורדה של הצופה
        if not run["ok"]:
            if visible_then_click(
                page,
                '[title*="Download"], [aria-label*="Download"], [aria-label*="הורדה"]',
                3000,
            ):
                saved4 = wait_and_save_download(
                    page, out_dir, base_name="bezeq_invoice_pdfjs", timeout_ms=15000
                )
                if saved4:
                    run.update(ok=True, path=saved4)
                elif pdf_responses:
                    saved5 = save_pdf_from_response(
                        pdf_responses[-1], out_dir, base_name="bezeq_invoice_pdfjs_resp"
                    )
                    if saved5:
                        run.update(ok=True, path=saved5)

        if take_screens:
            p_after = os.path.join(screenshots_dir, f"bezeq_{now_stamp()}_after.png")
            safe_screenshot(page, p_after, full_page=True, notes=run["notes"])

        if keep_trace:
            trace_path = os.path.join(out_dir, f"bezeq_trace_{now_stamp()}.zip")
            try:
                context.tracing.stop(path=trace_path)
                run["notes"].append(f"trace:{trace_path}")
            except Exception as e:
                run["notes"].append(f"trace_stop_failed:{e}")

        context.close()
        browser.close()

    return run


# -------------------- CLI --------------------


def main():
    ap = argparse.ArgumentParser(
        description="Bezeq (myinvoice) PDF fetcher – Flutter/Blob/PDF.js aware (v38.1)"
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
    ap.add_argument(
        "--headful", action="store_true", help="פתח דפדפן עם UI (נוח לדיבוג)"
    )
    ap.add_argument("--no-screenshots", action="store_true", help="אל תשמור צילומי מסך")
    ap.add_argument("--no-trace", action="store_true", help="אל תפיק playwright trace")
    args = ap.parse_args()

    out_dir = ensure_dir(args.out_dir)
    res = fetch_bezeq_pdf(
        url=args.url,
        out_dir=out_dir,
        timeout=args.timeout,
        headless=not args.headful,
        take_screens=(not args.no_screenshots),
        keep_trace=(not args.no_trace),
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if not res["ok"]:
        # קוד יציאה לא־אפס כדי שתזרום ל־quarantine אם משולב בסקריפט גדול
        sys.exit(2)


if __name__ == "__main__":
    main()
