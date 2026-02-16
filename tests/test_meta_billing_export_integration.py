from __future__ import annotations

import json
import sys
from pathlib import Path

from invplatform.cli import meta_billing_export as mbe


def _base_argv(out_dir: Path) -> list[str]:
    return [
        "meta_billing_export",
        "--api-version",
        "v24.0",
        "--business-id",
        "1351676656106280",
        "--ad-account",
        "1010624901159130",
        "--start",
        "2026-01-01",
        "--end",
        "2026-02-01",
        "--out",
        str(out_dir),
    ]


def test_integration_main_partial_success_non_strict(tmp_path, monkeypatch, capsys):
    out_dir = tmp_path / "out"
    monkeypatch.setenv("META_ACCESS_TOKEN", "tok")
    monkeypatch.setattr(sys, "argv", _base_argv(out_dir))

    monkeypatch.setattr(
        mbe,
        "fetch_business_invoices",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            mbe.GraphAPIError(
                {
                    "message": "(#100) Tried accessing nonexisting field (business_invoices) on node type (User)",
                    "type": "OAuthException",
                    "code": 100,
                }
            )
        ),
    )
    monkeypatch.setattr(
        mbe,
        "fetch_ad_account_activities",
        lambda *args, **kwargs: [
            {
                "event_type": "ad_account_billing_charge",
                "event_time": "2026-01-15T12:46:18+0000",
                "date_time_in_timezone": "1/15/2026 at 2:46 PM",
                "object_type": "ACCOUNT",
                "object_name": "Vadim Geshiktor",
                "extra_data": '{"currency":"ILS","new_value":700,"transaction_id":"tx-1"}',
            }
        ],
    )

    rc = mbe.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "[INFO] normalized --ad-account to act_1010624901159130" in out
    assert "node type (User)" in out
    assert "--business-id" in out
    assert (out_dir / "charges.json").exists()
    charges = json.loads((out_dir / "charges.json").read_text(encoding="utf-8"))
    assert len(charges) == 1


def test_integration_main_strict_fails_on_single_endpoint_error(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    argv = _base_argv(out_dir) + ["--strict"]

    monkeypatch.setenv("META_ACCESS_TOKEN", "tok")
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(
        mbe,
        "fetch_business_invoices",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            mbe.GraphAPIError(
                {
                    "message": "(#100) Tried accessing nonexisting field (business_invoices) on node type (User)",
                    "type": "OAuthException",
                    "code": 100,
                }
            )
        ),
    )
    monkeypatch.setattr(mbe, "fetch_ad_account_activities", lambda *args, **kwargs: [])

    rc = mbe.main()
    assert rc == 1
