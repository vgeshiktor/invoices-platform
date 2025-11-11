import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "apps" / "workers-py" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from invplatform.cli import graph_invoice_finder as graph  # noqa: E402


def test_filesystem_helpers(tmp_path):
    nested = tmp_path / "nested"
    path = graph.ensure_dir(str(nested))
    assert Path(path).exists()

    name = graph.sanitize_filename(" invoice:2025/06?.pdf ")
    assert name == "invoice_2025_06_.pdf"

    tag = graph.short_msg_tag("abc-123-XYZ", n=5)
    assert tag == "23XYZ"

    first = graph.ensure_unique_path(str(nested), "invoice", tag="tag")
    Path(first).write_text("one")
    second = graph.ensure_unique_path(str(nested), "invoice", tag="tag")
    assert first.endswith("__tag.pdf")
    assert second.endswith("__tag__2.pdf")


def test_hash_and_keyword_helpers():
    assert (
        graph.sha256_bytes(b"abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert graph.keyword_in_text("Invoice ready", "invoice", ignore_case=True)
    assert not graph.keyword_in_text("prefixinvoice", "invoice")
    assert graph.within_domain("https://billing.example.com/doc", ["example.com"])
    assert not graph.within_domain("notaurl", ["example.com"])


def test_pdf_keyword_stats_and_confidence(monkeypatch, tmp_path):
    monkeypatch.setattr(graph, "HAVE_PYMUPDF", True)

    class DummyPage:
        def __init__(self, text):
            self.text = text

        def get_text(self, mode):
            assert mode == "text"
            return self.text

    class DummyDoc:
        def __iter__(self):
            return iter([DummyPage("חשבונית מס קבלה ארנונה"), DummyPage("תלוש שכר")])

    monkeypatch.setattr(graph, "fitz", type("F", (), {"open": lambda *_: DummyDoc()}))

    path = tmp_path / "dummy.pdf"
    path.write_bytes(b"%PDF")

    stats = graph.pdf_keyword_stats(str(path))
    assert stats["pos_hits"] >= 1
    assert 0.0 <= graph.pdf_confidence(stats) <= 1.0


def test_message_relevance_helpers(monkeypatch, tmp_path):
    assert graph.should_consider_message("חשבונית מס קבלה", "")
    assert not graph.should_consider_message("תלוש שכר", "")

    dummy = tmp_path / "doc.pdf"
    dummy.write_text("")

    monkeypatch.setattr(
        graph,
        "pdf_keyword_stats",
        lambda _: {"pos_hits": 2, "neg_terms": []},
    )
    ok, stats = graph.decide_pdf_relevance(str(dummy), trusted_hint=False)
    assert ok and stats["pos_hits"] == 2

    monkeypatch.setattr(
        graph,
        "pdf_keyword_stats",
        lambda _: {"pos_hits": 0, "neg_terms": ["תלוש שכר"]},
    )
    ok, _ = graph.decide_pdf_relevance(str(dummy), trusted_hint=False)
    assert not ok

    monkeypatch.setattr(
        graph,
        "pdf_keyword_stats",
        lambda _: {"pos_hits": 0, "neg_terms": []},
    )
    ok, _ = graph.decide_pdf_relevance(str(dummy), trusted_hint=True)
    assert ok


def test_extract_links_from_html_and_text():
    html = """
    <html>
      <body>
        <a href="https://example.com/inv.pdf">Download</a>
        <a href="https://example.com/inv.pdf">Duplicate</a>
      </body>
    </html>
    """
    links = graph.extract_links_from_html(html)
    assert links == ["https://example.com/inv.pdf"]


def test_download_direct_pdf(monkeypatch):
    class DummyResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {
                "Content-Type": "application/pdf",
                "Content-Disposition": 'attachment; filename="inv.pdf"',
            }
            self.content = b"%PDF-stub"

    captured = {}

    def fake_get(url, headers, timeout):
        captured.update(headers)
        return DummyResponse()

    monkeypatch.setattr(graph.requests, "get", fake_get)

    result = graph.download_direct_pdf(
        "https://example.com/invoice",
        out_dir=".",
        referer="https://origin",
        ua="UA",
    )
    assert result is not None
    name, blob = result
    assert name == "inv.pdf"
    assert blob.startswith(b"%PDF")
    assert captured["Referer"] == "https://origin"
    assert captured["User-Agent"] == "UA"


def test_normalize_myinvoice_url():
    messy = "https://myinvoice.bezeq.co.il//?/foo\\&bar=1"
    assert (
        graph.normalize_myinvoice_url(messy)
        == "https://myinvoice.bezeq.co.il/?/foo&bar=1"
    )
