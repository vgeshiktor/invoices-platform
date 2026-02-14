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

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "invoices"
ARNONA_TEXT = (FIXTURES_DIR / "arnona_8UhU.txt").read_text(encoding="utf-8")
MUNICIPAL_TEXT = (FIXTURES_DIR / "municipal_8Uhc.txt").read_text(encoding="utf-8")


def test_invoice_record_to_csv_row_formats_numbers():
    record = report.InvoiceRecord(
        source_file="sample.pdf",
        base_before_vat=100.0,
        invoice_total=123.456,
        invoice_vat=None,
        notes="ok",
    )
    row = record.to_csv_row(
        ["source_file", "base_before_vat", "invoice_vat", "invoice_total", "notes"]
    )
    assert row == ["sample.pdf", "100.00", "", "123.46", "ok"]


def test_normalize_parse_and_select_amounts():
    assert report.normalize_amount_token("-1,234.50") == "-1234.50"
    assert report.normalize_amount_token("123.456") == "654.321"
    assert report.normalize_amount_token("00.976") == "976.00"
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


def test_infer_totals_prefers_municipal_block_sum():
    lines = [
        "line",
        'ח"שב',
        "100.0",
        "200.0",
        "סכנה",
        'סה"כ לתשלום 50.0',
    ]
    text = 'ארנונה סה"כ לתשלום 50.0'
    totals = report.infer_totals(lines, text, pdfminer_lines=lines)
    assert totals["invoice_total"] == pytest.approx(300.0)
    assert totals["breakdown_sum"] == pytest.approx(300.0)


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


def test_period_due_date_and_reference_helpers():
    text = "תקופה: 01/09/2025 - 30/09/2025 לתשלום עד 15.10.2025 PO #12345"
    start, end, label = report.extract_period_info(text)
    assert start == "2025-09-01"
    assert end == "2025-09-30"
    assert "2025-09" in (label or "")
    due = report.extract_due_date(text)
    assert due == "2025-10-15"
    refs = report.extract_reference_numbers(text)
    assert "12345" in refs


def test_classification_and_confidence_helpers():
    category, confidence, rule = report.classify_invoice(
        "חשבונית בזק שירותי אינטרנט", "בזק", False
    )
    assert category == "communication"
    assert confidence and confidence >= 0.8
    assert rule and "vendor" in rule
    rec = report.InvoiceRecord(
        source_file="a.pdf",
        invoice_total=100.0,
        invoice_vat=17.0,
        breakdown_sum=100.0,
        reference_numbers=["PO1234"],
        category="communication",
    )
    rec.period_start = "2025-09-01"
    rec.period_end = "2025-09-30"
    confidence_score = report.compute_parse_confidence(rec)
    assert confidence_score > 0.7


def test_file_sha256(tmp_path):
    target = tmp_path / "a.pdf"
    target.write_bytes(b"abc")
    digest = report.file_sha256(target)
    assert digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_extract_period_info_supports_ranges_and_bilingual_labels_text_sample():
    text = (
        "31/10/2025- ו30/09/2025- הוראת הקבע בחשבונך בבנק תחויב בשני תשלומים\n"
        "2025 אוקטובר-ספטמבר"
    )
    start, end, label = report.extract_period_info(text)
    assert start == "2025-09-01"
    assert end == "2025-10-30"
    assert label == "ספטמבר - אוקטובר"


def test_infer_invoice_date_fallback_grabs_first_numeric_text_sample():
    text = ARNONA_TEXT.replace("תאריך הדפסה:", "תאריך מדומה:")
    assert report.infer_invoice_date(text) == "01/09/2025"


def test_infer_invoice_from_municipal_text_text_sample():
    lines = report.extract_lines(MUNICIPAL_TEXT)[:5]
    assert report.infer_invoice_from(lines, MUNICIPAL_TEXT) == "עיריית פתח תקווה"


def test_extract_period_info_supports_ranges_and_bilingual_labels_fixture():
    start, end, label = report.extract_period_info(ARNONA_TEXT)
    assert start == "2025-09-01"
    assert end == "2025-10-30"
    assert label == "ספטמבר - אוקטובר"


def test_infer_invoice_date_fallback_grabs_first_numeric_fixture():
    assert report.infer_invoice_date(ARNONA_TEXT) == "01/09/2025"


def test_infer_invoice_from_municipal_text_fixture():
    lines = report.extract_lines(MUNICIPAL_TEXT)[:5]
    assert report.infer_invoice_from(lines, MUNICIPAL_TEXT) == "עיריית פתח תקווה"


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
        return [report.InvoiceRecord(source_file=path.name, invoice_total=10.0)]

    monkeypatch.setattr(report, "parse_invoices", fake_parse)

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
    header = csv_path.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header.index("base_before_vat") < header.index("invoice_vat")
    assert header.index("invoice_vat") < header.index("invoice_total")


def test_compute_report_totals_skips_missing_and_zero():
    records = [
        report.InvoiceRecord(
            source_file="a.pdf", invoice_total=100.0, invoice_vat=17.0
        ),
        report.InvoiceRecord(source_file="b.pdf", invoice_total=0.0, invoice_vat=0.0),
        report.InvoiceRecord(source_file="c.pdf", invoice_total=None, invoice_vat=None),
        report.InvoiceRecord(
            source_file="d.pdf", invoice_total=-20.0, invoice_vat=-3.0
        ),
    ]
    totals = report.compute_report_totals(records)
    assert totals["records"]["count"] == 4
    assert totals["invoice_total"]["sum"] == pytest.approx(80.0)
    assert totals["invoice_total"]["count"] == 2
    assert totals["invoice_total"]["missing"] == 1
    assert totals["invoice_total"]["zero"] == 1
    assert totals["invoice_total"]["negative"] == 1
    assert totals["invoice_total"]["positive"] == 1
    assert totals["invoice_total"]["abs_sum"] == pytest.approx(120.0)
    assert totals["invoice_total"]["avg"] == pytest.approx(40.0)
    assert totals["invoice_total"]["min"] == pytest.approx(-20.0)
    assert totals["invoice_total"]["max"] == pytest.approx(100.0)

    assert totals["invoice_vat"]["sum"] == pytest.approx(14.0)
    assert totals["invoice_vat"]["count"] == 2
    assert totals["invoice_vat"]["missing"] == 1
    assert totals["invoice_vat"]["zero"] == 1
    assert totals["invoice_vat"]["negative"] == 1
    assert totals["invoice_vat"]["positive"] == 1
    assert totals["invoice_vat"]["abs_sum"] == pytest.approx(20.0)
    assert totals["invoice_vat"]["avg"] == pytest.approx(7.0)
    assert totals["invoice_vat"]["min"] == pytest.approx(-3.0)
    assert totals["invoice_vat"]["max"] == pytest.approx(17.0)


def test_write_summary_csv_writes_metrics(tmp_path):
    totals = {
        "records": {"count": 2},
        "invoice_vat": {
            "sum": 14.0,
            "abs_sum": 20.0,
            "count": 2,
            "missing": 0,
            "zero": 0,
            "negative": 1,
            "positive": 1,
            "min": -3.0,
            "max": 17.0,
            "avg": 7.0,
        },
        "invoice_total": {
            "sum": 80.0,
            "abs_sum": 120.0,
            "count": 2,
            "missing": 1,
            "zero": 1,
            "negative": 1,
            "positive": 1,
            "min": -20.0,
            "max": 100.0,
            "avg": 40.0,
        },
    }
    path = tmp_path / "summary.csv"
    report.write_summary_csv(totals, path)
    rows = path.read_text(encoding="utf-8").splitlines()
    header = rows[0].split(",")
    assert header[:4] == ["metric", "sum", "abs_sum", "count"]
    assert rows[1].startswith("records,,,")
    assert rows[2].startswith("invoice_vat,14.00,20.00,2")
    assert rows[3].startswith("invoice_total,80.00,120.00,2")


def test_extract_partner_totals_from_text_handles_reversed_amounts():
    text = (
        'סה"כ חיובי החשבון לא כולל מע"מ%) 18 ( 42 . 975 { '
        'מע"מ% 18 58 . 175 { '
        'סה"כ חיובים וזיכויים לתקופת החשבון כולל מע"מ00 . 1,151 { '
        '00 . 1,151 {סה"כ לתשלום'
    )
    totals = report.extract_partner_totals_from_text(text)
    assert totals["invoice_total"] == pytest.approx(1151.0)
    assert totals["invoice_vat"] == pytest.approx(175.58)
    assert totals["base_before_vat"] == pytest.approx(975.42)


def test_report_writers_create_parent_dirs(tmp_path):
    nested = tmp_path / "reports" / "nested"
    json_path = nested / "out.json"
    csv_path = nested / "out.csv"
    summary_path = nested / "summary.csv"

    records = [report.InvoiceRecord(source_file="a.pdf", invoice_total=10.0)]
    report.write_json(records, json_path)
    report.write_csv(records, csv_path)
    report.write_summary_csv(report.compute_report_totals(records), summary_path)

    assert json_path.exists()
    assert csv_path.exists()
    assert summary_path.exists()


def test_infer_invoice_for_handles_details_marker():
    lines_simple = [
        "header line",
        "פירוט החיוב:",
        "שלטים 2025",
    ]
    assert report.infer_invoice_for(lines_simple) == "שלטים 2025"

    lines_with_amount = [
        "פירוט החיוב:",
        "955.50",
        "1020057002009 ' יתרת חוב שלט מס- 2025 שלטים",
    ]
    assert report.infer_invoice_for(lines_with_amount) == "שלטים 2025"


def test_find_municipal_invoice_id_uses_previous_line():
    lines = [
        "משולם בהוראת קבע",
        "גן ילדים/מעון- 39",
        "10200570020",
        "שורה אחרת",
    ]
    invoice_id, invoice_for = report.find_municipal_invoice_id(lines)
    assert invoice_id == "10200570020"
    assert invoice_for == "גן ילדים/מעון- 39"


def test_extract_municipal_breakdown_marks_discount_negative():
    lines = [
        "6,010.90 חיוב תקופתי ארנונה- 2026 ארנונה",
        "42.10 הנחת גביה בבנק- 2026 ארנונה",
    ]
    values = report.extract_municipal_breakdown(lines)
    assert values == [6010.9, -42.1]


def test_extract_amount_from_label_reads_word_line(monkeypatch):
    monkeypatch.setattr(report, "HAVE_PYMUPDF", True)

    class DummyPage:
        def __init__(self, words):
            self._words = words

        def get_text(self, mode):
            assert mode == "words"
            return self._words

    words = [
        (10.0, 100.0, 11.0, 101.0, 'סה"כ', 0, 0, 0),
        (20.0, 100.0, 21.0, 101.0, "יגבה", 0, 0, 1),
        (30.0, 100.0, 31.0, 101.0, "מהחשבון", 0, 0, 2),
        (40.0, 100.0, 41.0, 101.0, 'בש"ח:', 0, 0, 3),
        (80.0, 100.0, 81.0, 101.0, "1,234.50", 0, 0, 4),
    ]
    page = DummyPage(words)
    amount = report.extract_amount_from_label(page, ["יגבה"])
    assert amount == pytest.approx(1234.5)
