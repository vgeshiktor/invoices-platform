import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "apps" / "workers-py" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from invplatform.domain import constants as domain_constants  # noqa: E402
from invplatform.domain import files as domain_files  # noqa: E402
from invplatform.domain import pdf as domain_pdf  # noqa: E402
from invplatform.domain import relevance as domain_relevance  # noqa: E402


def test_ensure_dir_and_sanitize_filename(tmp_path):
    target = tmp_path / "nested" / "dir"
    created = domain_files.ensure_dir(str(target))
    assert Path(created).exists()

    cleaned = domain_files.sanitize_filename(" invoice:2025/06?.pdf ")
    assert cleaned == "invoice_2025_06_.pdf"
    assert domain_files.sanitize_filename("") == "invoice.pdf"


def test_short_msg_tag_and_unique_path(tmp_path):
    value = domain_files.short_msg_tag("abc123", n=4)
    assert value == "c123"
    assert domain_files.short_msg_tag("", n=4) == "msg"

    base_dir = tmp_path / "out"
    base_dir.mkdir()
    first = domain_files.ensure_unique_path(str(base_dir), "invoice", tag="tag")
    Path(first).write_text("one")
    second = domain_files.ensure_unique_path(str(base_dir), "invoice", tag="tag")
    assert first.endswith("__tag.pdf")
    assert second.endswith("__tag__2.pdf")


def test_sha256_bytes():
    digest = domain_files.sha256_bytes(b"abc")
    assert digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_keyword_and_body_helpers():
    assert domain_relevance.keyword_in_text(
        "Invoice ready", "invoice", ignore_case=True
    )
    assert not domain_relevance.keyword_in_text("coinvoicex", "invoice")
    assert domain_relevance.is_municipal_text(domain_constants.HEB_MUNICIPAL[0])
    assert domain_relevance.body_has_negative("מדווחים על תלוש שכר")
    assert domain_relevance.body_has_positive("חשבונית מס קבלה הוצאה")
    assert domain_relevance.should_consider_message("חשבונית מס קבלה", "")
    assert not domain_relevance.should_consider_message("תלוש שכר", "")
    assert domain_relevance.within_domain(
        "https://billing.example.com/invoice", ["example.com"]
    )
    assert not domain_relevance.within_domain("notaurl", ["example.com"])


def test_pdf_keyword_stats_and_confidence(monkeypatch, tmp_path):
    monkeypatch.setattr(domain_pdf, "HAVE_PYMUPDF", True)

    class DummyPage:
        def __init__(self, text):
            self._text = text

        def get_text(self, mode):
            assert mode == "text"
            return self._text

    class DummyDoc:
        def __init__(self, pages):
            self._pages = pages
            self.closed = False

        def __iter__(self):
            return iter(self._pages)

        def close(self):
            self.closed = True

    def fake_open(path):
        return DummyDoc(
            [
                DummyPage("Invoice ready for review"),
                DummyPage("This page mentions payslip salary details."),
                DummyPage("Extra page that should never be read"),
            ]
        )

    monkeypatch.setattr(domain_pdf, "fitz", SimpleNamespace(open=fake_open))

    pdf_path = tmp_path / "stub.pdf"
    pdf_path.write_bytes(b"%PDF")

    stats = domain_pdf.pdf_keyword_stats(str(pdf_path))
    assert stats["pos_hits"] >= 1
    assert stats["neg_hits"] >= 1  # stops scanning once a negative term is seen

    assert domain_pdf.pdf_confidence({"pos_hits": 3, "neg_hits": 1}) == pytest.approx(
        0.75
    )
    assert domain_pdf.pdf_confidence({"pos_hits": 0, "neg_hits": 0}) == 0.0
