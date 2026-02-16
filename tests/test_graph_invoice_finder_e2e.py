from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

import pytest

from tests.fixtures.graph_september_2025 import _pdf_bytes, build_september_2025_fixture


def _import_graph_invoice_finder():
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "apps" / "workers-py" / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from invplatform.cli import graph_invoice_finder as gif_module

    return gif_module


gif = _import_graph_invoice_finder()

_STUB_FIXTURE_OVERRIDE: Optional[Dict[str, object]] = None


class _StubGraphClient:
    """Replay recorded Graph API responses."""

    last_init: Dict[str, object] = {}

    def __init__(
        self,
        client_id: str,
        authority: str = "consumers",
        scopes: List[str] | None = None,
        token_cache_path: str | None = None,
        interactive_auth: bool = False,
        timeout: int = 60,
        max_retries: int = 4,
    ):
        fixture = _STUB_FIXTURE_OVERRIDE or build_september_2025_fixture()
        type(self).last_init = {
            "client_id": client_id,
            "authority": authority,
            "scopes": scopes,
            "token_cache_path": token_cache_path,
            "interactive_auth": interactive_auth,
            "timeout": timeout,
            "max_retries": max_retries,
        }
        self._messages = sorted(
            fixture["messages"], key=lambda m: m["received"], reverse=True
        )
        self._message_index: Dict[str, Dict[str, object]] = {
            m["id"]: m for m in fixture["messages"]
        }

    def get_wellknown_folder_id(self, wellknown: str) -> str | None:
        return "sent-folder" if wellknown == "sentitems" else None

    def iter_messages(
        self,
        start_iso: str,
        end_iso: str,
        page_size: int = 50,
        max_pages: int = 50,
        exclude_parent_ids: List[str] | None = None,
    ) -> Iterator[Dict[str, object]]:
        for msg in self._messages:
            if exclude_parent_ids and msg["parent"] in exclude_parent_ids:
                continue
            yield {
                "id": msg["id"],
                "subject": msg["subject"],
                "bodyPreview": msg["preview"],
                "from": {"emailAddress": {"address": msg["from_address"]}},
                "receivedDateTime": msg["received"],
                "webLink": msg["web_link"],
                "hasAttachments": msg["hasAttachments"],
                "parentFolderId": msg["parent"],
            }

    def list_attachments(self, msg_id: str) -> List[Dict[str, object]]:
        message = self._message_index[msg_id]
        attachments: Iterable[Dict[str, object]] = message["attachments"]
        return [
            {"id": att["id"], "name": att["name"], "contentType": att["contentType"]}
            for att in attachments
        ]

    def download_attachment(self, msg_id: str, att_id: str) -> bytes:
        message = self._message_index[msg_id]
        for att in message["attachments"]:
            if att["id"] == att_id:
                return att["content"]
        raise KeyError(f"attachment {att_id} not found for message {msg_id}")

    def get_message_body_html(self, msg_id: str) -> str:
        return self._message_index[msg_id]["body_html"]


def test_graph_invoice_finder_september_2025(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    global _STUB_FIXTURE_OVERRIDE
    _STUB_FIXTURE_OVERRIDE = None

    fixture = build_september_2025_fixture()
    direct_links: Dict[str, tuple[str, bytes]] = fixture["direct_links"]
    bezeq_links: Dict[str, tuple[str, bytes]] = fixture["bezeq_links"]
    expected = fixture["expected"]

    monkeypatch.setattr(gif, "HAVE_PYMUPDF", False)
    monkeypatch.setattr(gif, "GraphClient", _StubGraphClient)

    def _fake_download_direct_pdf(
        url: str, out_dir: str, referer: str | None = None, ua: str | None = None
    ):
        return direct_links.get(url)

    def _fake_bezeq_fetch_with_api_sniff(**kwargs):
        url = kwargs.get("url")
        if url not in bezeq_links:
            return {"ok": False, "path": None, "notes": ["no-fixture"]}
        name, blob = bezeq_links[url]
        return {"ok": True, "path": (name, blob), "notes": ["fixture"]}

    monkeypatch.setattr(gif, "download_direct_pdf", _fake_download_direct_pdf)
    monkeypatch.setattr(
        gif, "bezeq_fetch_with_api_sniff", _fake_bezeq_fetch_with_api_sniff
    )

    out_dir = tmp_path / "invoices"
    report_path = tmp_path / "download_report.json"
    saved_json_path = tmp_path / "saved.json"
    saved_csv_path = tmp_path / "saved.csv"

    argv = [
        "graph_invoice_finder",
        "--client-id",
        "stub-client",
        "--start-date",
        "2025-09-01",
        "--end-date",
        "2025-10-01",
        "--invoices-dir",
        str(out_dir),
        "--download-report",
        str(report_path),
        "--save-json",
        str(saved_json_path),
        "--save-csv",
        str(saved_csv_path),
        "--exclude-sent",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    gif.main()

    saved_files = sorted(p.name for p in out_dir.glob("*.pdf"))
    assert saved_files == sorted(name for _, name in expected)

    with saved_json_path.open("r", encoding="utf-8") as fh:
        saved_rows = json.load(fh)
    assert [row["id"] for row in saved_rows] == [msg_id for msg_id, _ in expected]
    assert sorted(Path(row["path"]).name for row in saved_rows) == saved_files

    with report_path.open("r", encoding="utf-8") as fh:
        report = json.load(fh)
    assert [row["id"] for row in report["saved"]] == [msg_id for msg_id, _ in expected]
    assert not report[
        "rejected"
    ], "No invoices should be rejected in the September baseline run."
    assert _StubGraphClient.last_init.get("interactive_auth") is False


def _rebuild_link_maps(
    messages: Iterable[Dict[str, object]],
) -> Tuple[Dict[str, Tuple[str, bytes]], Dict[str, Tuple[str, bytes]]]:
    direct_links: Dict[str, Tuple[str, bytes]] = {}
    bezeq_links: Dict[str, Tuple[str, bytes]] = {}
    for msg in messages:
        for entry in msg.get("direct_links", []):
            direct_links[entry["url"]] = (entry["name"], entry["content"])
        bezeq_entry = msg.get("bezeq_link")
        if bezeq_entry:
            bezeq_links[bezeq_entry["url"]] = (
                bezeq_entry["name"],
                bezeq_entry["content"],
            )
    return direct_links, bezeq_links


def test_graph_invoice_finder_cli_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
):
    global _STUB_FIXTURE_OVERRIDE

    fixture = build_september_2025_fixture()

    negative_msg = {
        "id": "AQMkNEGATIVE0000000000000000000000000000000000000000000000000000NEG",
        "subject": "תלוש שכר לחודש ספטמבר 2025",
        "preview": "תלוש שכר לעובד/ת",
        "from_address": "hr@example.com",
        "received": "2025-09-20T09:10:00Z",
        "web_link": "https://example.com/payroll",
        "parent": "sent-folder",
        "hasAttachments": True,
        "attachments": [
            {
                "id": "att-payroll",
                "name": "תלוש שכר ספטמבר.pdf",
                "contentType": "application/pdf",
                "content": _pdf_bytes("payroll-sept-2025"),
            }
        ],
        "body_html": "<html><body>תלוש שכר</body></html>",
    }

    ambiguous_msg = {
        "id": "AQMkAMBIGUOUS0000000000000000000000000000000000000000000000000AMB",
        "subject": "חשבונית מס עבור שירותי ייעוץ",
        "preview": "קובץ מצורף",
        "from_address": "billing@example.com",
        "received": "2025-09-12T11:22:33Z",
        "web_link": "https://example.com/invoice",
        "parent": "inbox",
        "hasAttachments": True,
        "attachments": [
            {
                "id": "att-ambiguous",
                "name": "ambiguous_service.pdf",
                "contentType": "application/pdf",
                "content": _pdf_bytes("ambiguous-content"),
            }
        ],
        "body_html": "<html><body>חשבונית</body></html>",
    }

    fixture["messages"].extend([negative_msg, ambiguous_msg])
    direct_links, bezeq_links = _rebuild_link_maps(fixture["messages"])
    fixture["direct_links"] = direct_links
    fixture["bezeq_links"] = bezeq_links
    expected_saved = list(fixture["expected"])

    _STUB_FIXTURE_OVERRIDE = fixture

    def _fake_download_direct_pdf(
        url: str, out_dir: str, referer: str | None = None, ua: str | None = None
    ):
        return fixture["direct_links"].get(url)

    def _fake_bezeq_fetch_with_api_sniff(**kwargs):
        url = kwargs.get("url")
        if url not in fixture["bezeq_links"]:
            return {"ok": False, "path": None, "notes": ["no-fixture"]}
        name, blob = fixture["bezeq_links"][url]
        return {"ok": True, "path": (name, blob), "notes": ["fixture"]}

    def _fake_pdf_keyword_stats(path: str) -> Dict[str, object]:
        data = Path(path).read_bytes().decode("utf-8", "ignore")
        if "payroll-sept-2025" in data:
            return {
                "pos_hits": 0,
                "neg_hits": 2,
                "pos_terms": [],
                "neg_terms": ["salary", "payroll"],
            }
        if "ambiguous-content" in data:
            return {
                "pos_hits": 0,
                "neg_hits": 1,
                "pos_terms": [],
                "neg_terms": ["uncertain"],
            }
        return {"pos_hits": 2, "neg_hits": 0, "pos_terms": ["invoice"], "neg_terms": []}

    monkeypatch.setattr(gif, "GraphClient", _StubGraphClient)
    monkeypatch.setattr(gif, "download_direct_pdf", _fake_download_direct_pdf)
    monkeypatch.setattr(
        gif, "bezeq_fetch_with_api_sniff", _fake_bezeq_fetch_with_api_sniff
    )
    monkeypatch.setattr(gif, "pdf_keyword_stats", _fake_pdf_keyword_stats)
    monkeypatch.setattr(gif, "HAVE_PYMUPDF", False)

    out_dir = tmp_path / "invoices"
    report_path = tmp_path / "download_report.json"
    saved_json_path = tmp_path / "saved.json"
    saved_csv_path = tmp_path / "saved.csv"
    candidates_path = tmp_path / "candidates.json"
    nonmatches_path = tmp_path / "nonmatches.json"
    cache_path = tmp_path / "msal_cache.bin"

    argv = [
        "graph_invoice_finder",
        "--client-id",
        "stub-client",
        "--authority",
        "common",
        "--interactive-auth",
        "--token-cache-path",
        str(cache_path),
        "--start-date",
        "2025-09-01",
        "--end-date",
        "2025-10-01",
        "--invoices-dir",
        str(out_dir),
        "--download-report",
        str(report_path),
        "--save-json",
        str(saved_json_path),
        "--save-csv",
        str(saved_csv_path),
        "--save-candidates",
        str(candidates_path),
        "--save-nonmatches",
        str(nonmatches_path),
        "--keep-quarantine",
        "--verify",
        "--explain",
        "--threshold-sweep",
        "0.40,0.70,0.90",
        "--bezeq-headful",
        "--bezeq-trace",
        "--bezeq-screenshots",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    try:
        gif.main()
    finally:
        _STUB_FIXTURE_OVERRIDE = None

    captured = capsys.readouterr()
    assert "Threshold sweep on saved invoices" in captured.out

    saved_files = sorted(p.name for p in out_dir.glob("*.pdf"))
    assert saved_files == sorted(name for _, name in expected_saved)

    quarantine_dir = out_dir / "quarantine"
    quarantined_files = list(quarantine_dir.rglob("*.pdf"))
    assert quarantined_files, "verify flag should place ambiguous invoice in quarantine"

    with saved_json_path.open("r", encoding="utf-8") as fh:
        saved_rows = json.load(fh)
    assert [row["id"] for row in saved_rows] == [msg_id for msg_id, _ in expected_saved]

    with candidates_path.open("r", encoding="utf-8") as fh:
        candidates = json.load(fh)
    assert len(candidates) >= len(expected_saved)
    assert any(c.get("decision") == "quarantine" for c in candidates)

    with nonmatches_path.open("r", encoding="utf-8") as fh:
        nonmatches = json.load(fh)
    assert any(entry.get("reason") == "negative_context" for entry in nonmatches)

    with report_path.open("r", encoding="utf-8") as fh:
        report = json.load(fh)
    assert any(
        r.get("ok") is False for r in report["report"]
    ), "quarantine entry expected in report"

    assert _StubGraphClient.last_init.get("authority") == "common"
    assert _StubGraphClient.last_init.get("interactive_auth") is True
    assert _StubGraphClient.last_init.get("token_cache_path") == str(cache_path)


def test_graph_invoice_finder_auth_required_exits_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
):
    class _AuthRequiredClient:
        def __init__(self, *args, **kwargs):  # noqa: D401, ANN002, ANN003
            raise RuntimeError("AUTH_REQUIRED: No cached token available.")

    monkeypatch.setattr(gif, "GraphClient", _AuthRequiredClient)
    argv = [
        "graph_invoice_finder",
        "--client-id",
        "stub-client",
        "--start-date",
        "2025-09-01",
        "--end-date",
        "2025-10-01",
        "--invoices-dir",
        str(tmp_path / "invoices"),
    ]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc:
        gif.main()

    out = capsys.readouterr().out
    assert exc.value.code == 2
    assert "AUTH_REQUIRED" in out
    assert "--interactive-auth" in out
