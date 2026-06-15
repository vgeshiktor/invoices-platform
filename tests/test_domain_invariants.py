import csv
import json
from pathlib import Path

from invplatform.cli import invoices_report as report
from invplatform.cli import monthly_invoices as monthly


def test_cross_provider_repeat_is_emitted_once_and_reruns_are_idempotent(tmp_path):
    gmail_dir = tmp_path / "gmail"
    outlook_dir = tmp_path / "outlook"
    dest_dir = tmp_path / "monthly"
    gmail_dir.mkdir()
    outlook_dir.mkdir()

    (gmail_dir / "gmail-copy.pdf").write_bytes(b"SAME-INVOICE")
    (outlook_dir / "graph-copy.pdf").write_bytes(b"SAME-INVOICE")

    first = monthly.consolidate_pdfs(dest_dir, [gmail_dir, outlook_dir])
    second = monthly.consolidate_pdfs(dest_dir, [gmail_dir, outlook_dir])

    assert first["copied"] == 1
    assert first["duplicates"] == 1
    assert second["copied"] == 0
    assert len(list(dest_dir.glob("*.pdf"))) == 1


def test_monthly_summary_marks_partial_failure_and_utc_half_open_window(tmp_path):
    dest_dir = tmp_path / "monthly"
    monthly.write_summary(
        dest_dir,
        start_date="2025-01-01",
        end_date="2025-02-01",
        label="01_2025",
        results=[
            monthly.ProviderResult("gmail", tmp_path / "gmail", ["gmail-cmd"], 0, 1.25),
            monthly.ProviderResult("outlook", tmp_path / "outlook", ["graph-cmd"], 1, 2.5),
        ],
        consolidation={"copied": 1, "duplicates": 0, "sources": 1, "existing": 0},
        dedupe={"gmail": {"kept": 1, "moved": 0}},
        stage_timings={"total_seconds": 3.75},
    )

    payload = json.loads((dest_dir / "run_summary.json").read_text(encoding="utf-8"))

    assert payload["status"] == "partial_failure"
    assert payload["successful_providers"] == ["gmail"]
    assert payload["failed_providers"] == ["outlook"]
    assert payload["date_interval_semantics"] == "[start_date, end_date)"
    assert payload["timezone"] == "UTC"


def test_report_outputs_round_money_redact_secrets_and_preserve_multilingual_text(tmp_path):
    json_path = tmp_path / "report.json"
    csv_path = tmp_path / "report.csv"
    summary_path = tmp_path / "summary.csv"
    records = [
        report.InvoiceRecord(
            source_file="/private/credentials.json",
            invoice_id="INV-001",
            invoice_date="2025-01-15",
            invoice_from='בזק Bezeq בע"מ',
            invoice_for="חשבונית Invoice bilingual",
            base_before_vat=2.005,
            invoice_vat=1.005,
            invoice_total=3.015,
            notes="Authorization: Bearer secret-token from /tmp/token.json via /tmp/.msal_token_cache.bin",
        )
    ]

    report.write_json(records, json_path)
    report.write_csv(records, csv_path)
    report.write_summary_csv(report.compute_report_totals(records), summary_path)

    json_text = json_path.read_text(encoding="utf-8")
    csv_text = csv_path.read_text(encoding="utf-8")
    summary_rows = list(csv.reader(summary_path.read_text(encoding="utf-8").splitlines()))
    payload = json.loads(json_text)

    assert "חשבונית Invoice bilingual" in json_text
    assert "בזק Bezeq" in csv_text
    assert payload[0]["base_before_vat"] == 2.01
    assert payload[0]["invoice_vat"] == 1.01
    assert payload[0]["invoice_total"] == 3.02
    assert "2.01" in csv_text
    assert "1.01" in csv_text
    assert "3.02" in csv_text
    assert "Authorization" not in json_text
    assert "Bearer secret-token" not in json_text
    assert "credentials.json" not in json_text
    assert "token.json" not in json_text
    assert ".msal_token_cache.bin" not in json_text
    assert "Authorization" not in csv_text
    assert "token.json" not in csv_text
    assert ".msal_token_cache.bin" not in csv_text
    assert summary_rows[2][0] == "invoice_vat"
