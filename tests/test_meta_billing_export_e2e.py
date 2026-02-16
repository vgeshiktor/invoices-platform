from __future__ import annotations

import csv
import json
import sys
from typing import Any

from invplatform.cli import meta_billing_export as mbe


class _FakeHTTPResponse:
    def __init__(
        self,
        *,
        json_data: dict[str, Any] | None = None,
        body: bytes = b"",
        status_code: int = 200,
    ):
        self._json_data = json_data
        self._body = body
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        if self._json_data is None:
            raise ValueError("no json payload")
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int = 131072):  # noqa: ARG002
        if self._body:
            yield self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001, D401
        return False


def test_e2e_meta_billing_export_cli_with_http_replay(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    calls: list[tuple[str, dict[str, Any] | None, bool]] = []
    api_base = "https://graph.facebook.com/v24.0"
    business_id = "1351676656106280"

    def fake_get(
        url: str,
        params: dict[str, Any] | None = None,
        timeout: int = 60,  # noqa: ARG001
        stream: bool = False,
    ):
        calls.append((url, params, stream))

        if stream:
            assert url.startswith("https://files.example.com/invoice-1.pdf")
            assert "access_token=tok" in url
            return _FakeHTTPResponse(body=b"%PDF-1.7 fixture")

        if url == f"{api_base}/{business_id}/business_invoices":
            assert params is not None
            assert params["issue_start_date"] == "2026-01-01"
            return _FakeHTTPResponse(
                json_data={
                    "data": [
                        {
                            "id": "inv_obj_1",
                            "invoice_id": "FBADS-INV-1",
                            "download_uri": "https://files.example.com/invoice-1.pdf",
                        }
                    ],
                    "paging": {"next": f"{api_base}/invoices_page_2"},
                }
            )
        if url == f"{api_base}/invoices_page_2":
            return _FakeHTTPResponse(json_data={"data": []})

        if url == f"{api_base}/act_1010624901159130/activities":
            assert params is not None
            assert params["since"] == 1767225600
            assert params["until"] == 1769904000
            return _FakeHTTPResponse(
                json_data={
                    "data": [
                        {
                            "event_type": "ad_account_billing_charge",
                            "event_time": "2026-01-15T12:46:18+0000",
                            "date_time_in_timezone": "1/15/2026 at 2:46 PM",
                            "object_type": "ACCOUNT",
                            "object_name": "Vadim Geshiktor",
                            "extra_data": '{"currency":"ILS","new_value":700,"transaction_id":"tx-1"}',
                        },
                        {
                            "event_type": "ad_account_name_change",
                            "event_time": "2026-01-15T10:00:00+0000",
                            "date_time_in_timezone": "1/15/2026 at 12:00 PM",
                        },
                    ],
                    "paging": {"next": f"{api_base}/activities_page_2"},
                }
            )
        if url == f"{api_base}/activities_page_2":
            return _FakeHTTPResponse(
                json_data={
                    "data": [
                        {
                            "event_type": "ad_account_billing_charge",
                            "event_time": "2026-01-16T12:00:00+0000",
                            "date_time_in_timezone": "1/16/2026 at 2:00 PM",
                            "object_type": "ACCOUNT",
                            "object_name": "Vadim Geshiktor",
                            "extra_data": {
                                "currency": "ILS",
                                "new_value": 1600,
                                "transaction_id": "tx-2",
                            },
                        }
                    ]
                }
            )

        raise AssertionError(f"unexpected URL: {url} params={params}")

    monkeypatch.setattr(mbe.requests, "get", fake_get)
    monkeypatch.setenv("META_ACCESS_TOKEN", "tok")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "meta_billing_export",
            "--api-version",
            "v24.0",
            "--business-id",
            business_id,
            "--ad-account",
            "1010624901159130",
            "--start",
            "2026-01-01",
            "--end",
            "2026-02-01",
            "--out",
            str(out_dir),
        ],
    )

    rc = mbe.main()
    assert rc == 0

    # Regression guard: numeric ad account is normalized to act_<id> for API calls.
    assert any(
        "/act_1010624901159130/activities" in url and not stream
        for url, _params, stream in calls
    )

    invoice_pdf = out_dir / "invoices" / "invoice_FBADS-INV-1.pdf"
    assert invoice_pdf.exists()
    assert invoice_pdf.read_bytes() == b"%PDF-1.7 fixture"

    charges = json.loads((out_dir / "charges.json").read_text(encoding="utf-8"))
    assert len(charges) == 2
    assert {c["event_type"] for c in charges} == {"ad_account_billing_charge"}

    enriched = json.loads(
        (out_dir / "charges_enriched.json").read_text(encoding="utf-8")
    )
    assert [row["transaction_id"] for row in enriched] == ["tx-1", "tx-2"]
    assert [row["amount"] for row in enriched] == [7.0, 16.0]

    with (out_dir / "receipt_candidates.csv").open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["transaction_id"] for r in rows] == ["tx-1", "tx-2"]
    assert rows[0]["suggested_filename"] == "Transaction #tx-1.pdf"
