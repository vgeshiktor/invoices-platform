#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bezeq_invoice_fetcher_v38.py

ייעוד:
- הורדת חשבונית/קבלה מקישור מייל של בזק (myinvoice.bezeq.co.il)
- מטפל בדפי Flutter Web + PDF.js + הורדות blob/new-tab + reCAPTCHA v3

איך מריצים (דוגמאות):
    python bezeq_invoice_fetcher_v38.py \
        --url "https://myinvoice.bezeq.co.il/?MailID=..." \
        --out-dir "./invoices_out" \
        --timeout 45 \
        --headful \
        --trace \
        --screenshots

תלויות:
    pip install playwright
    playwright install  # להריץ פעם אחת
    # אופציונלי ל־HAR/TRACE: אין צורך בתלויות נוספות

מה הקוד עושה בקצרה:
1) פותח Chromium עם accept_downloads=True, locale he-IL ו-UA סטנדרטי
2) טוען את כתובת בזק וממתין ל־networkidle + יציבות Flutter
3) מנסה "להורדה" (טקסט/aria/regex) → מחכה ל- download/popup/pdf-response
4) אם צריך, לוחץ קודם "לצפיה" ואז מוריד מתוך PDF.js
5) שומר PDF ושמות קבצים נקיים; שומר צילומי מסך/trace אם התבקש

הערות אבחון:
- אם עדיין לא עובד אצלך, הוסף --trace --screenshots ושלח את תיקיית out.
- אם יש הודעת reCAPTCHA/Invalid domain, יש סיכוי שדרוש רענון/המתנה נוספת/שינוי UA.
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
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name.strip())
    return name or default


def now_stamp() -> str:
    return dt.utcnow().strftime("%Y%m%d_%H%M%S")


def ensure_dir(p: str) -> str:
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)
    return p


def visible_then_click(page, locator_query: str, timeout_ms: int = 4000) -> bool:
    """ניסיון שקוף: המתנה ל־locator ואז קליק. מחזיר True אם הצליח."""
    try:
        loc = page.locator(locator_query).first
        loc.wait_for(state="visible", timeout=timeout_ms)
        loc.scroll_into_view_if_needed()
        loc.click()
        return True
    except Exception:
        return False


def try_click_by_texts(page, texts: List[str], timeout_ms: int = 4000) -> bool:
    """חיפוש טקסטים במספר תצורות (טקסט רגיל/regex/יוניקוד)."""
    for t in texts:
        # נסיון 1: text= selector
        if visible_then_click(page, f'text="{t}"', timeout_ms):
            return True
        if visible_then_click(page, f"text={t}", timeout_ms):
            return True
        # נסיון 2: role=link/button עם שם
        if visible_then_click(page, f'role=link[name="{t}"]', timeout_ms):
            return True
        if visible_then_click(page, f'role=button[name="{t}"]', timeout_ms):
            return True
        # נסיון 3: regex יוניקוד
        pattern = re.sub(r"([().\[\]^$*+?{}|\\])", r"\\\1", t)
        if visible_then_click(page, f"text=/{pattern}/", timeout_ms):
            return True
    return False


def scan_dom_for_hebrew_and_click(
    page, words_regex: str, timeout_ms: int = 5000
) -> bool:
    """
    Fallback: מחפש DOM spans/links עם טקסט עברי תואם (גם אם זה Flutter HTML renderer),
    ומקליק באמצעות JS (להבטיח קליק גם על אלמנטים שקשים למיקוד).
    """
    try:
        page.wait_for_timeout(300)  # תן לרנדר להתייצב
        found = page.evaluate(
            """(pattern) => {
                const rx = new RegExp(pattern);
                const all = Array.from(document.querySelectorAll('a,button,span,div,[role="link"],[role="button"]'));
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
    """אוסף תגובות PDF + חלונות קופצים + אירועי הורדה."""
    page.context.set_default_timeout(30000)

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
    """מחכה ל־page.download ושומר. מחזיר הנתיב אם הצליח."""
    try:
        with page.expect_download(timeout=timeout_ms) as dl_info:
            # כלום – רק לחכות; הלחיצה כבר נעשתה לפני הקריאה לפונקציה
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
    """מוריד גוף תגובה PDF ושומר לקובץ."""
    try:
        body = resp.body()
        fname = sanitize_filename(base_name + ".pdf")
        out_path = os.path.join(out_dir, fname)
        with open(out_path, "wb") as f:
            f.write(body)
        return out_path
    except Exception:
        return None


def fetch_bezeq_pdf(
    url: str,
    out_dir: str,
    timeout: int = 45,
    headless: bool = False,
    take_screens: bool = True,
    keep_trace: bool = True,
) -> dict:
    """
    נכנס לקישור חשבונית בזק ומנסה להוריד PDF, עם כל מנגנוני ה־fallback.
    מחזיר dict עם פרטי ההרצה והתוצאה.
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

        # לוגי קונסול לצורך דיבוג
        page.on(
            "console", lambda m: run["notes"].append(f"console:{m.type()}:{m.text()}")
        )
        page.on("pageerror", lambda e: run["notes"].append(f"pageerror:{e}"))

        # SNIF PDF
        pdf_responses: List = []
        attach_pdf_sniffer(page, pdf_responses)

        page.set_default_timeout(timeout * 1000)
        page.goto(url, wait_until="domcontentloaded")
        # תן ל־Flutter להיטען
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except PWTimeout:
            run["notes"].append("networkidle_timeout")

        if take_screens:
            p = os.path.join(screenshots_dir, f"bezeq_{now_stamp()}_before.png")
            page.screenshot(path=p, full_page=True)
            run["notes"].append(f"screenshot:{p}")

        # נסיון ללחוץ "להורדה" ישירות
        clicked = (
            try_click_by_texts(page, ["להורדה", "לצפייה", "לצפיה"])
            or
            # aria-label/title
            visible_then_click(page, '[aria-label*="הורדה"],[title*="הורדה"]')
            or
            # יוניקוד
            try_click_by_texts(page, [HE_UNICODE_DL, HE_UNICODE_VIEW])
            or
            # Fallback: חיפוש טקסט בדום
            scan_dom_for_hebrew_and_click(page, r"(להורד[הא]|לצפ(י|י)ה)")
        )

        if not clicked:
            # יתכן שצריך לגלול כדי שהכפתור יופיע (כמו ברשימה של חשבוניות)
            page.mouse.wheel(0, 1000)
            time.sleep(0.5)
            clicked = (
                try_click_by_texts(page, ["להורדה", "לצפייה", "לצפיה"])
                or visible_then_click(page, '[aria-label*="הורדה"],[title*="הורדה"]')
                or scan_dom_for_hebrew_and_click(page, r"(להורד[הא]|לצפ(י|י)ה)")
            )

        if not clicked:
            run["notes"].append("click_failed: לא נמצא כפתור להורדה/לצפיה")
        else:
            run["notes"].append("clicked_download_or_view")

        # 1) נסיון לתפוס download event
        saved = wait_and_save_download(
            page, out_dir, base_name="bezeq_invoice", timeout_ms=15000
        )
        if saved:
            run.update(ok=True, path=saved)
        else:
            # 2) אולי זה פתח חלון חדש (popup)
            try:
                with context.expect_page(timeout=5000) as pop_ev:
                    # יתכן שהקליק כבר יצר popup; אם לא – זה יפיל Timeout
                    pass
                newp = pop_ev.value
                attach_pdf_sniffer(newp, pdf_responses)
                if take_screens:
                    p = os.path.join(screenshots_dir, f"bezeq_{now_stamp()}_popup.png")
                    newp.screenshot(path=p, full_page=True)
                    run["notes"].append(f"popup_screenshot:{p}")

                # חכה להורדה גם שם
                saved2 = wait_and_save_download(
                    newp, out_dir, base_name="bezeq_invoice_popup", timeout_ms=15000
                )
                if saved2:
                    run.update(ok=True, path=saved2)
                else:
                    # או PDF response
                    time.sleep(2.0)
            except PWTimeout:
                pass

        # 3) תגובות PDF שנתפסו ע"י ה־sniffer
        if not run["ok"] and pdf_responses:
            # קח את האחרונה
            resp = pdf_responses[-1]
            saved3 = save_pdf_from_response(
                resp, out_dir, base_name="bezeq_invoice_resp"
            )
            if saved3:
                run.update(ok=True, path=saved3)
            else:
                run["notes"].append("pdf_response_save_failed")

        # 4) אם לחצנו "לצפיה" אבל אין הורדה, נסה להוריד מתוך PDF.js
        if not run["ok"]:
            # כפתור הורדה של PDF.js
            dl_clicked = visible_then_click(
                page,
                '[title*="Download"], [aria-label*="Download"], [aria-label*="הורדה"]',
                3000,
            )
            if dl_clicked:
                saved4 = wait_and_save_download(
                    page, out_dir, base_name="bezeq_invoice_pdfjs", timeout_ms=15000
                )
                if saved4:
                    run.update(ok=True, path=saved4)
                else:
                    # אולי התגובה PDF נאספה
                    if pdf_responses:
                        resp = pdf_responses[-1]
                        saved5 = save_pdf_from_response(
                            resp, out_dir, base_name="bezeq_invoice_pdfjs_resp"
                        )
                        if saved5:
                            run.update(ok=True, path=saved5)

        if take_screens:
            p2 = os.path.join(screenshots_dir, f"bezeq_{now_stamp()}_after.png")
            try:
                page.screenshot(path=p2, full_page=True)
                run["notes"].append(f"screenshot:{p2}")
            except Exception:
                pass

        if keep_trace:
            trace_path = os.path.join(out_dir, f"bezeq_trace_{now_stamp()}.zip")
            context.tracing.stop(path=trace_path)
            run["notes"].append(f"trace:{trace_path}")

        context.close()
        browser.close()

    return run


def main():
    ap = argparse.ArgumentParser(
        description="Bezeq (myinvoice) PDF fetcher – Flutter/Blob/PDF.js aware"
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
        sys.exit(2)


if __name__ == "__main__":
    main()
