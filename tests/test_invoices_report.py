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
        report, "parse_invoices", lambda path, debug=False: [sample_record]
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


def test_cli_writes_vat_fields_in_order(monkeypatch, tmp_path):
    json_out = tmp_path / "report.json"
    csv_out = tmp_path / "report.csv"
    summary_out = tmp_path / "report.summary.csv"
    dummy_pdf = tmp_path / "sample.pdf"
    dummy_pdf.write_text("stub")

    sample_record = report.InvoiceRecord(
        source_file=dummy_pdf.name,
        base_before_vat=100.0,
        invoice_vat=17.0,
        invoice_total=117.0,
    )

    monkeypatch.setattr(
        report, "parse_invoices", lambda path, debug=False: [sample_record]
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
        "--summary-csv-output",
        str(summary_out),
    ]
    monkeypatch.setattr(sys, "argv", argv)

    report.main()
    header = csv_out.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header.index("base_before_vat") < header.index("invoice_vat")
    assert header.index("invoice_vat") < header.index("invoice_total")
    assert summary_out.exists()


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
    assert record.invoice_total == pytest.approx(23.42, rel=1e-3)
    assert record.invoice_vat == pytest.approx(3.57, rel=1e-3)
    assert record.base_before_vat == pytest.approx(19.85, rel=1e-3)


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


def test_bezeq_invoice_totals(monkeypatch):
    record = _parse_fixture_invoice(monkeypatch, "bezeq_80927472.txt")
    assert record.invoice_total == pytest.approx(894.63, rel=1e-3)
    assert record.invoice_vat == pytest.approx(136.47, rel=1e-3)


def test_keren_invoice_fields(monkeypatch):
    record = _parse_fixture_invoice(monkeypatch, "keren_3147.txt")
    assert record.invoice_from == "קרן-מדריכת הורים ותינוקות"
    assert record.invoice_id == "3147"
    assert record.invoice_for == "חוג תנועה ספטמבר 2025"
    assert record.category == "services"
    assert record.category_rule and record.category_rule.startswith("vendor:")


def test_ofek_invoice_fields(monkeypatch):
    record = _parse_fixture_invoice(monkeypatch, "ofek_productions_5857.txt")
    assert record.invoice_from == "אופק הפקות"
    assert record.invoice_id == "5857"
    assert record.invoice_for == "חוג תיאטרון חודש ספטמבר | חוג תיאטרון חודש אוגוסט"
    assert record.category == "services"
    assert record.category_rule and record.category_rule.startswith("vendor:")


def test_stingtv_invoice_fields(monkeypatch):
    record = _parse_fixture_invoice(monkeypatch, "stingtv_09_2025.txt")
    assert record.invoice_from == "STINGTV"
    assert record.invoice_for == "שירותי תוכן בינלאומיים | ספריות וערוצי פרימיום"
    assert record.category == "communication"
    assert record.category_rule and record.category_rule.startswith("vendor:")
    assert record.breakdown_values == [99.8, 35.0, 0.0]
    assert record.breakdown_sum == pytest.approx(record.invoice_total, rel=1e-3)


class _FakePage:
    def __init__(self, text, words):
        self._text = text
        self._words = words

    def get_text(self, kind="text"):
        if kind == "text":
            return self._text
        if kind == "words":
            return self._words
        raise ValueError(f"Unsupported kind: {kind}")


class _FakeDoc:
    def __init__(self, pages):
        self._pages = pages

    def __iter__(self):
        return iter(self._pages)

    def close(self):
        return None


class _FakeFitz:
    def __init__(self, doc):
        self._doc = doc

    def open(self, _path):
        return self._doc


def _make_municipal_page(invoice_id, invoice_for, total, breakdown_values):
    lines = [
        "משולם בהוראת קבע",
        'סה"כ יגבה מהחשבון בש"ח:',
        invoice_for,
        invoice_id,
        "27/02/2026",
        f"{abs(breakdown_values[0]):,.2f} חיוב תקופתי ארנונה- 2026 ארנונה",
        f"{abs(breakdown_values[1]):,.2f} הנחת גביה בבנק- 2026 ארנונה",
    ]
    text = "\n".join(lines)
    y_coord = 100.0
    words = [
        (10.0, y_coord, 11.0, y_coord + 1, 'סה"כ', 0, 0, 0),
        (20.0, y_coord, 21.0, y_coord + 1, "יגבה", 0, 0, 1),
        (30.0, y_coord, 31.0, y_coord + 1, "מהחשבון", 0, 0, 2),
        (40.0, y_coord, 41.0, y_coord + 1, 'בש"ח:', 0, 0, 3),
        (80.0, y_coord, 81.0, y_coord + 1, f"{total:,.2f}", 0, 0, 4),
    ]
    return _FakePage(text, words)


def test_parse_invoices_splits_municipal_direct_debit(monkeypatch):
    base_record = report.InvoiceRecord(
        source_file="sample.pdf",
        invoice_from="עיריית פתח תקווה",
        invoice_vat=0.0,
        municipal=True,
    )
    pages = [
        _make_municipal_page(
            "10200570020", "גן ילדים/מעון- 39", 5968.8, [6010.9, -42.1]
        ),
        _make_municipal_page("10200570021", "קרקע תפוסה- 516", 315.6, [317.8, -2.2]),
        _make_municipal_page(
            "10200700015", "חנייה בתעריף קרקע תפוסה- 510", 126.2, [127.1, -0.9]
        ),
    ]
    monkeypatch.setattr(report, "HAVE_PYMUPDF", True)
    monkeypatch.setattr(report, "fitz", _FakeFitz(_FakeDoc(pages)))
    monkeypatch.setattr(report, "parse_invoice", lambda path, debug=False: base_record)

    records = report.parse_invoices(Path("sample.pdf"))
    assert len(records) == 3
    by_id = {rec.invoice_id: rec for rec in records}
    assert by_id["10200570020"].invoice_total == pytest.approx(5968.8, rel=1e-3)
    assert by_id["10200570020"].breakdown_values == [6010.9, -42.1]
    assert by_id["10200570020"].invoice_for == "גן ילדים/מעון- 39"
    assert by_id["10200570020"].invoice_vat == pytest.approx(0.0)
    assert by_id["10200570020"].data_source == "pymupdf"


def test_parse_invoices_skips_split_on_duplicate_ids(monkeypatch):
    base_record = report.InvoiceRecord(
        source_file="sample.pdf",
        invoice_from="עיריית פתח תקווה",
        invoice_total=999.0,
        municipal=True,
    )
    pages = [
        _make_municipal_page(
            "10200570020", "גן ילדים/מעון- 39", 5968.8, [6010.9, -42.1]
        ),
        _make_municipal_page("10200570020", "גן ילדים/מעון- 39", 315.6, [317.8, -2.2]),
    ]
    monkeypatch.setattr(report, "HAVE_PYMUPDF", True)
    monkeypatch.setattr(report, "fitz", _FakeFitz(_FakeDoc(pages)))
    monkeypatch.setattr(report, "parse_invoice", lambda path, debug=False: base_record)

    records = report.parse_invoices(Path("sample.pdf"))
    assert records == [base_record]


def test_parse_invoices_skips_when_not_municipal(monkeypatch):
    base_record = report.InvoiceRecord(
        source_file="sample.pdf",
        invoice_total=10.0,
        municipal=False,
    )
    monkeypatch.setattr(report, "parse_invoice", lambda path, debug=False: base_record)

    records = report.parse_invoices(Path("sample.pdf"))
    assert records == [base_record]
