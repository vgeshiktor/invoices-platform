import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "apps" / "workers-py" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from invplatform.cli import invoices_report as report  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "invoices"


def _parse_fixture_invoice(monkeypatch, fixture_name: str):
    text = (FIXTURES_DIR / fixture_name).read_text(encoding="utf-8")
    lines = report.extract_lines(text)
    monkeypatch.setattr(report, "extract_text", lambda path: text)
    monkeypatch.setattr(report, "extract_text_with_pymupdf", lambda path: text)
    monkeypatch.setattr(report, "extract_lines", lambda _text: lines)
    monkeypatch.setattr(
        report, "file_sha256", lambda path: f"fixture-hash-{fixture_name}"
    )
    return report.parse_invoice(Path(fixture_name).with_suffix(".pdf"), debug=False)


def test_municipal_invoice_breakdown_matches_total(monkeypatch):
    record = _parse_fixture_invoice(monkeypatch, "municipal_8Uhc.txt")
    assert record.invoice_total == pytest.approx(6619.5, rel=1e-3)
    assert record.invoice_vat == pytest.approx(0.0)
    assert record.breakdown_sum == pytest.approx(record.invoice_total, rel=1e-6)
    assert record.breakdown_values
    assert len(record.breakdown_values) >= 4


def test_cli_handles_files_flag_and_debug(monkeypatch, tmp_path, capsys):
    json_out = tmp_path / "report.json"
    csv_out = tmp_path / "report.csv"
    dummy_pdf = tmp_path / "sample.pdf"
    dummy_pdf.write_text("stub")

    sample_record = report.InvoiceRecord(
        source_file=dummy_pdf.name,
        invoice_total=6619.5,
        invoice_vat=0.0,
        breakdown_sum=6619.5,
        breakdown_values=[1.0],
    )

    monkeypatch.setattr(
        report, "parse_invoice", lambda path, debug=False: sample_record
    )

    argv = [
        "invoices_report",
        "--input-dir",
        str(tmp_path),
        "--files",
        dummy_pdf.name,
        "--json-output",
        str(json_out),
        "--csv-output",
        str(csv_out),
        "--debug",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    report.main()
    captured = capsys.readouterr()
    assert "Generated 1 records" in captured.out

    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert len(data) == 1
    entry = data[0]
    assert entry["invoice_total"] == pytest.approx(6619.5, rel=1e-3)
    assert entry["invoice_vat"] == pytest.approx(0.0)
    assert entry["breakdown_sum"] == pytest.approx(entry["invoice_total"], rel=1e-6)
    assert entry["breakdown_values"]


def test_arnona_invoice_extracts_period_and_details(monkeypatch):
    record = _parse_fixture_invoice(monkeypatch, "arnona_8UhU.txt")
    assert record.invoice_from == "עיריית פתח תקווה"
    assert record.invoice_for == "ארנונה לעסקים"
    assert record.period_start == "2025-09-01"
    assert record.period_end == "2025-10-30"
    assert record.period_label == "ספטמבר - אוקטובר"


def test_parse_invoice_municipal_regression(monkeypatch):
    record = _parse_fixture_invoice(monkeypatch, "municipal_8Uhc.txt")
    assert record.invoice_id == "4553051904"
    assert record.invoice_date == "28/08/2025"
    assert record.invoice_from == "עיריית פתח תקווה"


def test_rami_levy_invoice_from_detected(monkeypatch):
    record = _parse_fixture_invoice(monkeypatch, "rami_levy_RAMIPDF.txt")
    assert record.invoice_from == "רמי לוי תקשורת"
    assert not record.municipal
    assert record.category == "communication"
    assert record.category_rule and record.category_rule.startswith("vendor:")


def test_ravkav_invoice_parsing(monkeypatch):
    record = _parse_fixture_invoice(monkeypatch, "ravkav_topup.txt")
    assert record.invoice_total == pytest.approx(10.0, rel=1e-3)
    assert record.invoice_vat == pytest.approx(1.53, rel=1e-3)
    assert record.invoice_for == "רב-קו - טעינה"
    assert record.vat_rate == pytest.approx(18.0, rel=1e-3)
    assert record.category == "transportation"
    assert record.category_rule and record.category_rule.startswith("vendor:")


def test_partner_postpaid_invoice_totals(monkeypatch):
    record = _parse_fixture_invoice(monkeypatch, "partner_postpaid_998018687.txt")
    assert record.invoice_id == "6523791025"
    assert record.invoice_total == pytest.approx(976.0, rel=1e-3)
    assert record.invoice_vat == pytest.approx(148.88, rel=1e-3)
    assert record.base_before_vat == pytest.approx(827.12, rel=1e-3)
    assert record.invoice_from == 'חברת פרטנר תקשורת בע"מ'
    assert (
        record.invoice_for
        == "5 מנויי סלולר | 1 מנוי תמסורת 01-0-9017125 | תנועות כלליות בחשבון הלקוח"
    )
    assert record.category == "communication"
