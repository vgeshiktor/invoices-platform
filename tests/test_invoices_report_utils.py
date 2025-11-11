import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "apps" / "workers-py" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from invplatform.cli import invoices_report as report  # noqa: E402


def test_invoice_record_to_csv_row_formats_numbers():
    record = report.InvoiceRecord(
        source_file="sample.pdf",
        invoice_total=123.456,
        invoice_vat=None,
        notes="ok",
    )
    row = record.to_csv_row(["source_file", "invoice_total", "invoice_vat", "notes"])
    assert row == ["sample.pdf", "123.46", "", "ok"]


def test_normalize_parse_and_select_amounts():
    assert report.normalize_amount_token("-1,234.50") == "-1234.50"
    assert report.normalize_amount_token("123.456") == "654.321"
    assert report.parse_number("bad") is None
    tokens = ["0020", "12.30", "100", "5.555"]
    assert report.select_amount(tokens) == pytest.approx(12.30)


def test_amount_near_markers_and_find_amount_before_marker():
    text = 'טרם 10.00\nסה"כ לתשלום\nעוד שורת 20,25 ו 90'
    assert report.amount_near_markers(
        text, [r"סה\"כ"], window=40, prefer="max"
    ) == pytest.approx(20.25)
    assert report.amount_near_markers(
        text, [r"סה\"כ"], window=40, prefer="min"
    ) == pytest.approx(10.0)

    lines = [
        "שורה קודמת ₪ 250.00",
        'סה"כ לתשלום 17%',
        "שורה הבאה ₪ 200.00",
    ]
    assert report.find_amount_before_marker(lines, 'סה"כ לתשלום') == pytest.approx(
        250.0
    )
    assert (
        report.find_amount_before_marker(lines, 'סה"כ לתשלום', prefer_inline=True)
        is None
    )


def test_numeric_helpers_and_blocks():
    lines = [
        "line 1",
        'מ"עמ ינפל 500.00',
        "line 3 200",
        "line 4 100",
    ]
    values = report.numeric_values_near_marker(lines, 'מ"עמ ינפל')
    assert 500.0 in values and 200.0 in values

    block_lines = ['ח"שב', "1,000.00", "250", "סכנה"]
    block_sum, entries = report.sum_numeric_block(
        block_lines,
        ['ח"שב'],
        ["סכנה"],
    )
    assert block_sum == pytest.approx(1250.0)
    assert entries == [1000.0, 250.0]


def test_needs_fallback_extract_lines_and_search_patterns():
    assert report.needs_fallback_text("") is True
    assert report.needs_fallback_text("a" * 10) is True
    glyphy = "a" * 300 + " (cid:1) (cid:2) (cid:3) (cid:4) (cid:5) (cid:6)"
    assert report.needs_fallback_text(glyphy)

    lines = report.extract_lines(" line1 \r\n\n line2 ")
    assert lines == ["line1", "line2"]

    match = report.search_patterns([r"סה\"כ[: ]+([\d.]+)"], 'סה"כ 123.45')
    assert match == "123.45"


def test_extract_text_with_pymupdf_stub(monkeypatch, tmp_path):
    monkeypatch.setattr(report, "HAVE_PYMUPDF", True)

    class DummyPage:
        def __init__(self, text, should_fail=False):
            self.text = text
            self.should_fail = should_fail

        def get_text(self, mode):
            if self.should_fail:
                raise RuntimeError("boom")
            assert mode == "text"
            return self.text

    class DummyDoc:
        def __init__(self, pages):
            self.pages = pages

        def __iter__(self):
            return iter(self.pages)

        def close(self):
            pass

    def fake_open(path):
        return DummyDoc(
            [
                DummyPage("first page"),
                DummyPage("fail", should_fail=True),
                DummyPage("last"),
            ]
        )

    monkeypatch.setattr(report, "fitz", SimpleNamespace(open=fake_open))
    pdf_path = tmp_path / "dummy.pdf"
    pdf_path.write_bytes(b"%PDF")
    text = report.extract_text_with_pymupdf(pdf_path)
    assert "first page" in text and "last" in text


def test_infer_totals_uses_fallback_patterns():
    lines = [
        "line",
        'מ"עמ ינפל 500.00',
        'לע מ"עמ 90.00',
    ]
    text = """
    סה"כ לתשלום 590.00
    סה"כ מע"מ 90.00
    ₪ 590.00
    """
    totals = report.infer_totals(lines, text)
    assert totals["invoice_total"] == pytest.approx(590.0)
    assert totals["invoice_vat"] == pytest.approx(90.0)


def test_infer_totals_municipal_block_enforces_zero_vat():
    block_lines = ['ח"שב', "100", "200", 'סה"', "closing"]
    text = "דרישת תשלום ארנונה"
    totals = report.infer_totals(
        ["noop"],
        text,
        pdfminer_lines=block_lines,
    )
    assert totals["municipal"] is True
    assert totals["invoice_total"] == pytest.approx(300.0)
    assert totals["invoice_vat"] == 0.0
    assert totals["breakdown_values"] == [100.0, 200.0]


def test_generate_report_and_writers(tmp_path, monkeypatch):
    invoices_dir = tmp_path / "invoices"
    invoices_dir.mkdir()
    file_a = invoices_dir / "a.pdf"
    file_b = invoices_dir / "b.pdf"
    file_a.write_text("stub")
    file_b.write_text("stub")
    captured = []

    def fake_parse(path, debug=False):
        captured.append(path.name)
        return report.InvoiceRecord(source_file=path.name, invoice_total=10.0)

    monkeypatch.setattr(report, "parse_invoice", fake_parse)

    records = report.generate_report(
        invoices_dir, selected_files=["a.pdf", "missing.pdf"], debug=True
    )
    assert [rec.source_file for rec in records] == ["a.pdf"]
    assert captured == ["a.pdf"]

    json_path = tmp_path / "out.json"
    csv_path = tmp_path / "out.csv"
    report.write_json(records, json_path)
    report.write_csv(records, csv_path)
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded[0]["invoice_total"] == 10.0
    assert "source_file" in csv_path.read_text(encoding="utf-8")
