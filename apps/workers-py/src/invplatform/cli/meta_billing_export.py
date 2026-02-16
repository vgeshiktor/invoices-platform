#!/usr/bin/env python3
"""
meta_billing_export.py
======================

מטרה
----
לשלוף בצורה "פרוגרומטית-נוחה" את מה שאפשר מתוך Meta Ads billing:

1) Monthly invoices (אם קיימות אצלך) דרך:
   GET /{BUSINESS_ID}/business_invoices
   ולעיתים הורדה של PDF דרך download_uri.

2) יומן חיובים (billing charge events) דרך:
   GET /{AD_ACCOUNT_ID}/activities
   וסינון event_type == "ad_account_billing_charge"
   (נותן metadata על חיובים; לא מבטיח PDF קבלה לכל חיוב)

שימוש
-----
1) התקנה:
   pip install requests

2) קבע טוקן בסביבה:
   export META_ACCESS_TOKEN="EAAB..."

3) הרצה:
   python meta_billing_export.py \
     --api-version v24.0 \
     --business-id 123456789 \
     --ad-account act_987654321 \
     --start 2026-01-01 \
     --end   2026-02-01 \
     --out ./out_meta_billing

פלט
---
out_meta_billing/
  invoices.json
  invoices/                  (PDFs אם הצלחנו להוריד)
  charges.json
  charges.csv

הערות חשובות
------------
- אם אתה משלם "תשלומים אוטומטיים לפי סף" ייתכן שלא יהיו monthly invoices בכלל.
- כדי לקבל היסטוריה מלאה ב-activities צריך since/until + pagination.
- אם אין לך הרשאות Finance מתאימות, חלק מהדברים יחזרו ריק/שגיאת הרשאה.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

import requests


class GraphAPIError(RuntimeError):
    def __init__(self, error: Dict[str, Any]):
        self.error = error
        self.code = error.get("code")
        self.err_type = error.get("type")
        self.message = error.get("message", "Graph API error")
        self.fbtrace_id = error.get("fbtrace_id")
        super().__init__(f"Graph API error: {error}")


def iso_to_unix(iso_date: str) -> int:
    # Date בלבד (00:00:00 UTC) לצורך since/until
    d = dt.date.fromisoformat(iso_date)
    return int(dt.datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=dt.timezone.utc).timestamp())


def graph_get(url: str, params: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=timeout)
    try:
        data = r.json()
    except Exception:
        r.raise_for_status()
        raise

    # Graph API לפעמים מחזיר error בתוך JSON
    if isinstance(data, dict) and "error" in data:
        raise GraphAPIError(data["error"])
    return data


def paginate_edge(first_url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    משיכה עם pagination לפי paging.next (אם קיים).
    """
    out: List[Dict[str, Any]] = []
    url = first_url
    p = dict(params)

    while True:
        data = graph_get(url, p)
        items = data.get("data", [])
        if isinstance(items, list):
            out.extend(items)

        paging = data.get("paging") or {}
        next_url = paging.get("next")
        if not next_url:
            break

        # כשיש next_url, הוא כבר כולל את ה-access_token והפרמטרים,
        # אז נעבור אליו ישירות בלי params נוספים.
        url = next_url
        p = {}

    return out


def ensure_access_token_in_url(download_url: str, access_token: str) -> str:
    """
    חלק מה-download_uri עובדים כמו שהם, חלק דורשים token.
    אם אין access_token בפרמטרים – נוסיף.
    """
    u = urlparse(download_url)
    q = parse_qs(u.query)
    if "access_token" not in q:
        q["access_token"] = [access_token]
        new_query = urlencode(q, doseq=True)
        return urlunparse((u.scheme, u.netloc, u.path, u.params, new_query, u.fragment))
    return download_url


def download_file(url: str, dest: Path, timeout: int = 120) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)


def fetch_business_invoices(
    api_base: str, business_id: str, start: str, end: str, access_token: str
) -> List[Dict[str, Any]]:
    # לפי הדוקו: issue_start_date inclusive, issue_end_date exclusive.
    # נבקש גם download_uri אם קיים.
    url = f"{api_base}/{business_id}/business_invoices"
    params = {
        "access_token": access_token,
        "issue_start_date": start,
        "issue_end_date": end,
        "limit": 200,
        "fields": ",".join(
            [
                "id",
                "invoice_id",
                "invoice_date",
                "billing_period_start",
                "billing_period_end",
                "amount_due",
                "currency",
                "advertiser_name",
                "type",
                "download_uri",
            ]
        ),
    }
    return paginate_edge(url, params)


def fetch_ad_account_activities(
    api_base: str, ad_account: str, start: str, end: str, access_token: str
) -> List[Dict[str, Any]]:
    """
    Activities מחזיר שבוע כברירת מחדל, לכן אנחנו נותנים since/until.
    נמשוך טווח זמן, ואז נסנן מקומית ל-event_type של חיוב.
    """
    url = f"{api_base}/{ad_account}/activities"
    params = {
        "access_token": access_token,
        "since": iso_to_unix(start),
        "until": iso_to_unix(end),
        "limit": 500,
        "fields": ",".join(
            [
                "actor_name",
                "application_name",
                "date_time_in_timezone",
                "event_time",
                "event_type",
                "extra_data",
                "object_name",
                "object_type",
                "translated_event_type",
            ]
        ),
    }
    return paginate_edge(url, params)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_charges_csv(path: Path, charges: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # נשמור עמודות "בטוחות" (extra_data יכול להיות אובייקט מורכב)
    fields = [
        "event_time",
        "date_time_in_timezone",
        "event_type",
        "translated_event_type",
        "object_type",
        "object_name",
        "actor_name",
        "application_name",
        "extra_data_json",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in charges:
            row = {k: c.get(k) for k in fields if k not in ("extra_data_json",)}
            row["extra_data_json"] = json.dumps(
                parse_extra_data(c.get("extra_data")), ensure_ascii=False
            )
            w.writerow(row)


def parse_extra_data(extra_data: Any) -> Any:
    if isinstance(extra_data, dict):
        return extra_data
    if isinstance(extra_data, str):
        txt = extra_data.strip()
        if txt.startswith("{") and txt.endswith("}"):
            try:
                return json.loads(txt)
            except Exception:
                return extra_data
    return extra_data


def to_major_units(minor_amount: Any) -> Optional[float]:
    if not isinstance(minor_amount, (int, float)):
        return None
    return round(float(minor_amount) / 100.0, 2)


def enrich_charges(charges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for c in charges:
        parsed = parse_extra_data(c.get("extra_data"))
        tx_id = parsed.get("transaction_id") if isinstance(parsed, dict) else None
        amount_minor = parsed.get("new_value") if isinstance(parsed, dict) else None
        currency = parsed.get("currency") if isinstance(parsed, dict) else None
        out.append(
            {
                **c,
                "extra_data_parsed": parsed,
                "transaction_id": tx_id,
                "amount_minor": amount_minor,
                "amount": to_major_units(amount_minor),
                "currency": currency,
            }
        )
    return out


def write_receipt_candidates_csv(path: Path, charges: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "event_time",
        "date_time_in_timezone",
        "transaction_id",
        "currency",
        "amount_minor",
        "amount",
        "suggested_filename",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in charges:
            tx = c.get("transaction_id")
            w.writerow(
                {
                    "event_time": c.get("event_time"),
                    "date_time_in_timezone": c.get("date_time_in_timezone"),
                    "transaction_id": tx,
                    "currency": c.get("currency"),
                    "amount_minor": c.get("amount_minor"),
                    "amount": c.get("amount"),
                    "suggested_filename": f"Transaction #{tx}.pdf" if tx else "",
                }
            )


def print_graph_error_context(
    scope: str, err: GraphAPIError, ad_account: Optional[str] = None
) -> None:
    print(f"[WARN] {scope} fetch failed: {err}")
    msg = err.message or ""
    code = err.code

    if (
        scope == "invoices"
        and code == 100
        and "business_invoices" in msg
        and "node type (User)" in msg
    ):
        print(
            "[HINT] --business-id צריך להיות Business Manager ID (node type Business), לא מזהה משתמש."
        )
        print("[HINT] אפשר למצוא Business ID ב-Meta Business Settings -> Business Info.")
        print("[HINT] ודא שלטוקן יש הרשאות business/finance מתאימות.")

    if scope == "activities" and code == 200 and ("ads_management" in msg or "ads_read" in msg):
        print("[HINT] הטוקן חסר ads_read או ads_management עבור חשבון המודעות.")
        if ad_account:
            print(f"[HINT] ודא שלמשתמש יש גישה ל-{ad_account} בממשק Meta Business.")
        print("[HINT] צור מחדש META_ACCESS_TOKEN עם ההרשאות הנדרשות.")

    if (
        scope == "activities"
        and code == 100
        and "activities" in msg
        and "node type (InvalidID)" in msg
    ):
        print("[HINT] --ad-account חייב להיות מזהה חשבון מודעות תקין (בדרך כלל בפורמט act_<id>).")
        if ad_account:
            print(f"[HINT] הערך שהועבר: {ad_account}")


def normalize_ad_account(ad_account: str) -> str:
    trimmed = ad_account.strip()
    if trimmed.startswith("act_"):
        return trimmed
    if trimmed.isdigit():
        return f"act_{trimmed}"
    return trimmed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-version", default="v24.0", help="למשל v24.0")
    ap.add_argument("--business-id", required=True, help="Business ID מספרי")
    ap.add_argument("--ad-account", required=True, help="Ad account בפורמט act_XXXXXXXXX")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD (exclusive)")
    ap.add_argument("--out", default="./out_meta_billing", help="תיקיית פלט")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="יציאה עם קוד שגיאה אם שליפת invoices או activities נכשלה",
    )
    args = ap.parse_args()

    access_token = os.environ.get("META_ACCESS_TOKEN")
    if not access_token:
        print("ERROR: נא להגדיר META_ACCESS_TOKEN בסביבה", file=sys.stderr)
        return 2

    api_base = f"https://graph.facebook.com/{args.api_version}"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    ad_account = normalize_ad_account(args.ad_account)
    if ad_account != args.ad_account:
        print(f"[INFO] normalized --ad-account to {ad_account}")

    # 1) Invoices
    invoices: List[Dict[str, Any]] = []
    invoices_failed = False
    try:
        invoices = fetch_business_invoices(
            api_base, args.business_id, args.start, args.end, access_token
        )
        write_json(out_dir / "invoices.json", invoices)
        print(f"[OK] invoices fetched: {len(invoices)}")
        if not invoices:
            print(
                "[INFO] business_invoices החזיר 0. זה תקין בחשבונות עם חיובי threshold/receipt במקום חשבוניות חודשיות."
            )
    except GraphAPIError as e:
        invoices_failed = True
        print_graph_error_context("invoices", e)
    except Exception as e:
        invoices_failed = True
        print(f"[WARN] invoices fetch failed: {e}")

    # ננסה להוריד PDFs אם יש download_uri
    inv_pdf_dir = out_dir / "invoices"
    downloaded = 0
    for inv in invoices:
        dl = inv.get("download_uri")
        inv_id = inv.get("invoice_id") or inv.get("id") or "unknown"
        if not dl:
            continue
        try:
            dl2 = ensure_access_token_in_url(dl, access_token)
            dest = inv_pdf_dir / f"invoice_{inv_id}.pdf"
            download_file(dl2, dest)
            downloaded += 1
        except Exception as e:
            print(f"[WARN] invoice download failed ({inv_id}): {e}")
    if invoices:
        print(f"[OK] invoice PDFs downloaded: {downloaded}")

    # 2) Activities → billing charges
    activities: List[Dict[str, Any]] = []
    activities_failed = False
    try:
        activities = fetch_ad_account_activities(
            api_base, ad_account, args.start, args.end, access_token
        )
        write_json(out_dir / "activities_raw.json", activities)
        print(f"[OK] activities fetched: {len(activities)}")
        if not activities:
            print(
                "[INFO] activities החזיר 0. בדוק ש--ad-account הוא החשבון שבאמת חויב בטווח התאריכים."
            )
    except GraphAPIError as e:
        activities_failed = True
        print_graph_error_context("activities", e, ad_account=ad_account)
    except Exception as e:
        activities_failed = True
        print(f"[WARN] activities fetch failed: {e}")

    charges = [a for a in activities if a.get("event_type") == "ad_account_billing_charge"]
    charges_enriched = enrich_charges(charges)
    write_json(out_dir / "charges.json", charges)
    write_json(out_dir / "charges_enriched.json", charges_enriched)
    write_charges_csv(out_dir / "charges.csv", charges)
    write_receipt_candidates_csv(out_dir / "receipt_candidates.csv", charges_enriched)
    if activities_failed:
        print("[WARN] billing charges extracted: 0 (activities unavailable)")
    else:
        print(f"[OK] billing charges extracted: {len(charges)}")
        with_txn = sum(1 for c in charges_enriched if c.get("transaction_id"))
        print(f"[OK] receipt candidates with transaction_id: {with_txn}")
        if with_txn:
            print(
                "[INFO] קבצי PDF של receipts לחיובי threshold לרוב מורדים ממסך Billing לפי transaction_id."
            )
            print(f"[INFO] ראה: {(out_dir / 'receipt_candidates.csv').resolve()}")
    print(f"[DONE] output dir: {out_dir.resolve()}")

    if args.strict and (invoices_failed or activities_failed):
        return 1
    if invoices_failed and activities_failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
