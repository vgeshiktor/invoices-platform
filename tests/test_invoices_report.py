import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "apps" / "workers-py" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from invplatform.cli import invoices_report as report  # noqa: E402


MUNICIPAL_PDF = REPO_ROOT / "invoices_outlook" / "333836120__8UhcAAAA.pdf"


pytestmark = pytest.mark.skipif(
    not report.HAVE_PYMUPDF,
    reason="PyMuPDF fallback required to read glyph-based PDFs",
)


def test_municipal_invoice_breakdown_matches_total():
    record = report.parse_invoice(MUNICIPAL_PDF, debug=False)
    assert record.invoice_total == pytest.approx(6619.5, rel=1e-3)
    assert record.invoice_vat == pytest.approx(0.0)
    assert record.breakdown_sum == pytest.approx(record.invoice_total, rel=1e-6)
    assert record.breakdown_values
    assert len(record.breakdown_values) >= 4


def test_cli_handles_files_flag_and_debug(monkeypatch, tmp_path, capsys):
    json_out = tmp_path / "report.json"
    csv_out = tmp_path / "report.csv"

    argv = [
        "invoices_report",
        "--input-dir",
        str(REPO_ROOT / "invoices_outlook"),
        "--files",
        MUNICIPAL_PDF.name,
        "--json-output",
        str(json_out),
        "--csv-output",
        str(csv_out),
        "--debug",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    report.main()
    captured = capsys.readouterr()
    assert "=== pdfminer text preview ===" in captured.out
    assert "=== PyMuPDF text preview ===" in captured.out

    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert len(data) == 1
    entry = data[0]
    assert entry["invoice_total"] == pytest.approx(6619.5, rel=1e-3)
    assert entry["invoice_vat"] == pytest.approx(0.0)
    assert entry["breakdown_sum"] == pytest.approx(entry["invoice_total"], rel=1e-6)
    assert entry["breakdown_values"]
