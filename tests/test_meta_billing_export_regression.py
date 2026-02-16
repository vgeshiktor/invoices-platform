from __future__ import annotations

import csv
import json
import sys

from invplatform.cli import meta_billing_export as mbe


def test_regression_invalid_id_hint_is_emitted(tmp_path, monkeypatch, capsys):
    out_dir = tmp_path / "out"
    monkeypatch.setenv("META_ACCESS_TOKEN", "tok")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "meta_billing_export",
            "--api-version",
            "v24.0",
            "--business-id",
            "1351676656106280",
            "--ad-account",
            "9610446569077918",
            "--start",
            "2026-01-01",
            "--end",
            "2026-02-01",
            "--out",
            str(out_dir),
        ],
    )
    monkeypatch.setattr(mbe, "fetch_business_invoices", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        mbe,
        "fetch_ad_account_activities",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            mbe.GraphAPIError(
                {
                    "message": "(#100) Tried accessing nonexisting field (activities) on node type (InvalidID)",
                    "type": "OAuthException",
                    "code": 100,
                }
            )
        ),
    )

    rc = mbe.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "[HINT] --ad-account חייב להיות מזהה חשבון מודעות תקין" in out
    assert "act_9610446569077918" in out


def test_regression_write_charges_csv_parses_stringified_extra_data(tmp_path):
    out_csv = tmp_path / "charges.csv"
    mbe.write_charges_csv(
        out_csv,
        [
            {
                "event_time": "2026-01-15T12:46:18+0000",
                "date_time_in_timezone": "1/15/2026 at 2:46 PM",
                "event_type": "ad_account_billing_charge",
                "translated_event_type": "Account billed",
                "object_type": "ACCOUNT",
                "object_name": "Vadim Geshiktor",
                "actor_name": "System",
                "application_name": "Meta ads",
                "extra_data": '{"currency":"ILS","new_value":700,"transaction_id":"tx-123"}',
            }
        ],
    )

    with out_csv.open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    parsed = json.loads(rows[0]["extra_data_json"])
    assert parsed["transaction_id"] == "tx-123"
    assert parsed["new_value"] == 700
