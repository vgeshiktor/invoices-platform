import base64
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "apps" / "workers-py" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from invplatform.cli import gmail_invoice_finder as gmail  # noqa: E402


def test_parse_headers_and_extract_parts():
    payload = {
        "headers": [
            {"name": "Subject", "value": "Invoice"},
            {"name": "From", "value": "sender@example.com"},
        ],
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": base64.urlsafe_b64encode(b"plain").decode()},
                    },
                    {
                        "mimeType": "text/html",
                        "body": {
                            "data": base64.urlsafe_b64encode(b"<b>html</b>").decode()
                        },
                    },
                ],
            }
        ],
    }
    headers = gmail.parse_headers(payload)
    assert headers == {"subject": "Invoice", "from": "sender@example.com"}

    html, plain = gmail.get_body_text(payload)
    assert "html" in html and "plain" in plain

    parts = gmail.extract_parts(payload)
    assert len(parts) == 4  # root payload + multipart container + two body parts


def test_extract_parts_handles_none():
    assert gmail.extract_parts(None) == []


def test_get_body_text_handles_bad_base64():
    payload = {
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": "###invalid###"},
            }
        ]
    }
    html, plain = gmail.get_body_text(payload)
    assert html == ""
    assert plain == ""


def test_normalize_link_and_links_from_message():
    redirect = "https://www.google.com/url?q=https%3A%2F%2Fexample.com%2Finv.pdf"
    normalized = gmail.normalize_link(redirect)
    assert normalized == "https://example.com/inv.pdf"

    html = '<a href="https://example.com/doc.pdf">Download</a>'
    plain = "Visit https://example.com/doc.pdf and https://www.google.com/url?q=https%3A%2F%2Fexample.com%2Finv.pdf"
    links = gmail.links_from_message(html, plain)
    assert links == ["https://example.com/doc.pdf", "https://example.com/inv.pdf"]

    mixed = gmail.links_from_message("<a href='mailto:test'>mail</a>", "not a link")
    assert mixed == []


def test_extract_links_from_html_empty():
    assert gmail.extract_links_from_html("") == []


def test_normalize_link_handles_falsey_and_objects():
    assert gmail.normalize_link("") == ""
    obj = object()
    assert gmail.normalize_link(obj) is obj


def test_decode_data_url_and_sha256_file(tmp_path):
    payload = base64.b64encode(b"%PDF").decode()
    data_url = f"data:application/pdf;base64,{payload}"
    assert gmail._decode_data_url(data_url) == b"%PDF"
    assert gmail._decode_data_url("invalid") is None
    assert gmail._decode_data_url("data:text/plain;base64,@@@") is None

    path = tmp_path / "file.pdf"
    path.write_bytes(b"abc")
    digest = gmail.sha256_file(str(path))
    assert digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    missing = gmail.sha256_file(str(path) + "_missing")
    assert missing is None


def test_load_existing_hash_index_filters(tmp_path):
    inv_dir = tmp_path / "invoices"
    (inv_dir / "_tmp").mkdir(parents=True)
    (inv_dir / "quarantine").mkdir()
    (inv_dir / "keep.pdf").write_bytes(b"A")
    (inv_dir / "skip.txt").write_text("noop")
    index = gmail.load_existing_hash_index(str(inv_dir))
    assert len(index) == 1
    assert next(iter(index.values())).endswith("keep.pdf")
    assert gmail.load_existing_hash_index(str(tmp_path / "missing")) == {}


def test_download_direct_pdf_fallback(monkeypatch):
    calls = []

    class DummyResponse:
        def __init__(self, status, headers, content):
            self.status_code = status
            self.headers = headers
            self.content = content

    responses = [
        DummyResponse(403, {"Content-Type": "application/pdf"}, b""),
        DummyResponse(
            200,
            {
                "Content-Type": "application/pdf",
                "Content-Disposition": 'attachment; filename="inv.pdf"',
            },
            b"%PDF-1.4",
        ),
    ]

    def fake_get(url, headers, timeout):
        calls.append(headers)
        return responses.pop(0)

    monkeypatch.setattr(gmail.requests, "get", fake_get)

    result = gmail.download_direct_pdf(
        "https://example.com/invoice",
        referer="https://origin",
        ua="UA",
        verbose=True,
    )
    assert result is not None
    name, blob = result
    assert name == "inv.pdf"
    assert blob.startswith(b"%PDF")
    assert any("Referer" in call for call in calls)
    assert calls[-1].get("Referer") is None


def test_download_direct_pdf_yes_headers(monkeypatch):
    captured = {}

    class DummyResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {
                "Content-Type": "application/octet-stream",
                "Content-Disposition": "attachment; filename=inv",
            }
            self.content = b"%PDF"

    def fake_get(url, headers, timeout):
        captured.update(headers)
        return DummyResponse()

    monkeypatch.setattr(gmail.requests, "get", fake_get)

    result = gmail.download_direct_pdf(
        "https://svc.yes.co.il/invoice", ua="UA", verbose=False
    )
    assert result[0] == "inv.pdf"
    assert captured["Origin"] == "https://www.yes.co.il"
    assert captured["sec-ch-ua-platform"] == '"macOS"'


def test_normalize_myinvoice_url():
    messy = "https://myinvoice.bezeq.co.il//?/foo\\&bar=1"
    assert (
        gmail.normalize_myinvoice_url(messy)
        == "https://myinvoice.bezeq.co.il/?/foo&bar=1"
    )


def test_sender_domain_and_trust_detection():
    addr = "Rav-Pass by HopOn <support@ravpass.co.il>"
    assert gmail.sender_domain(addr) == "ravpass.co.il"
    assert gmail.is_trusted_sender(addr)
    assert gmail.is_trusted_sender("support@ravpass.co.il")
    assert not gmail.is_trusted_sender("alerts@example.com")


def test_should_consider_message():
    assert gmail.should_consider_message("חשבונית מס קבלה", "")
    assert not gmail.should_consider_message("תלוש שכר", "")
