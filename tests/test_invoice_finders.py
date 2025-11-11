import base64
import hashlib
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "apps" / "workers-py" / "src"
sys.path.insert(0, str(SRC_DIR))

from invplatform.domain import files as domain_files  # noqa: E402
from invplatform.domain import pdf as domain_pdf  # noqa: E402
from invplatform.domain import relevance as domain_relevance  # noqa: E402


def _ensure_module(module_name: str) -> types.ModuleType:
    parts = module_name.split(".")
    for idx in range(1, len(parts) + 1):
        partial = ".".join(parts[:idx])
        if partial not in sys.modules:
            sys.modules[partial] = types.ModuleType(partial)
        if idx > 1:
            parent = sys.modules[".".join(parts[: idx - 1])]
            setattr(parent, parts[idx - 1], sys.modules[partial])
    return sys.modules[module_name]


def _stub_external_dependencies():
    sync_api = _ensure_module("playwright.sync_api")

    class DummyTimeoutError(Exception):
        pass

    class DummyManager:
        def __call__(self):
            return self

        def __enter__(self):
            raise RuntimeError("playwright stub: not available in tests")

        def __exit__(self, exc_type, exc, tb):
            return False

    sync_api.TimeoutError = DummyTimeoutError  # type: ignore[attr-defined]
    sync_api.sync_playwright = DummyManager()  # type: ignore[attr-defined]

    msal_mod = _ensure_module("msal")

    class DummyPCA:
        def __init__(self, *args, **kwargs):
            pass

        def initiate_device_flow(self, *args, **kwargs):
            raise RuntimeError("msal stub: not available in tests")

        def acquire_token_by_device_flow(self, *args, **kwargs):
            raise RuntimeError("msal stub: not available in tests")

    msal_mod.PublicClientApplication = DummyPCA  # type: ignore[attr-defined]

    creds_mod = _ensure_module("google.oauth2.credentials")

    class DummyCredentials:
        pass

    creds_mod.Credentials = DummyCredentials  # type: ignore[attr-defined]

    flow_mod = _ensure_module("google_auth_oauthlib.flow")

    class DummyFlow:
        def __init__(self, *args, **kwargs):
            pass

        @classmethod
        def from_client_secrets_file(cls, *args, **kwargs):
            raise RuntimeError("google_auth stub: not available in tests")

        def run_local_server(self, *args, **kwargs):
            raise RuntimeError("google_auth stub: not available in tests")

    flow_mod.InstalledAppFlow = DummyFlow  # type: ignore[attr-defined]

    transport_mod = _ensure_module("google.auth.transport.requests")

    class DummyRequest:
        pass

    transport_mod.Request = DummyRequest  # type: ignore[attr-defined]

    discovery_mod = _ensure_module("googleapiclient.discovery")

    def _dummy_build(*args, **kwargs):
        raise RuntimeError("googleapiclient stub: not available in tests")

    discovery_mod.build = _dummy_build  # type: ignore[attr-defined]


_stub_external_dependencies()


from invplatform.cli import gmail_invoice_finder as GMAIL  # noqa: E402


def test_domain_relevance_positive_keyword():
    assert domain_relevance.should_consider_message("חשבונית מס קבלה", "")
    assert domain_relevance.should_consider_message("Invoice for services", "")


def test_domain_relevance_negative_filter():
    assert not domain_relevance.should_consider_message("תלוש שכר יוני", "")
    assert not domain_relevance.should_consider_message("Salary payment", "")


def test_domain_files_unique_path(tmp_path):
    base_dir = tmp_path / "out"
    base_dir.mkdir()

    first = domain_files.ensure_unique_path(str(base_dir), "חשבונית:2025/06.pdf")
    Path(first).write_bytes(b"pdf")
    second = domain_files.ensure_unique_path(str(base_dir), "חשבונית:2025/06.pdf")

    assert first.endswith("חשבונית_2025_06.pdf")
    assert second.endswith("__2.pdf")


def test_domain_pdf_confidence_ratio():
    stats = {"pos_hits": 2, "neg_hits": 1}
    assert pytest.approx(domain_pdf.pdf_confidence(stats)) == pytest.approx(2 / 3)
    stats = {"pos_hits": 0, "neg_hits": 0}
    assert domain_pdf.pdf_confidence(stats) == 0.0


def test_gmail_build_query_includes_keywords():
    query = GMAIL.build_gmail_query("2025-06-01", "2025-07-01")
    assert "after:2025/06/01" in query
    assert "before:2025/07/01" in query
    assert "-in:sent" in query and "-from:me" in query
    assert "filename:pdf" in query
    assert query.endswith("in:anywhere")


def test_gmail_build_query_without_excluding_sent():
    query = GMAIL.build_gmail_query("2025-06-01", "2025-07-01", exclude_sent=False)
    assert "-in:sent" not in query
    assert "-from:me" not in query


def test_gmail_extract_links_deduplicates_and_captures():
    pytest.importorskip("bs4")
    html = """
    <html>
      <body>
        <a href="https://example.com/invoice.pdf">Download</a>
        <a href="https://example.com/invoice.pdf">Download Again</a>
        <img usemap="#map1">
        <map name="map1">
          <area href="https://example.com/area.pdf" />
        </map>
      </body>
    </html>
    """
    links = GMAIL.extract_links_from_html(html)
    assert links == [
        "https://example.com/invoice.pdf",
        "https://example.com/area.pdf",
    ]

    text_links = GMAIL.extract_links_from_text(
        "Visit https://example.com/invoice.pdf and https://example.com/invoice.pdf"
    )
    assert text_links == ["https://example.com/invoice.pdf"]


def test_gmail_normalize_link_unwraps_google_redirect():
    url = "https://www.google.com/url?q=https%3A%2F%2Fexample.com%2Finv.pdf&sa=D"
    assert GMAIL.normalize_link(url) == "https://example.com/inv.pdf"
    assert (
        GMAIL.normalize_link("https://example.com/file.pdf")
        == "https://example.com/file.pdf"
    )


def test_gmail_decode_data_url_roundtrip():
    payload = b"%PDF-1.7 stub"
    data_url = f"data:application/pdf;base64,{base64.b64encode(payload).decode()} "
    assert GMAIL._decode_data_url(data_url) == payload  # noqa: SLF001
    assert GMAIL._decode_data_url("not-a-data-url") is None  # noqa: SLF001


def test_gmail_load_existing_hash_index(tmp_path):
    invoices_dir = tmp_path / "invoices"
    (invoices_dir / "_tmp").mkdir(parents=True)
    (invoices_dir / "quarantine").mkdir(parents=True)
    (invoices_dir / "nested").mkdir(parents=True)

    (invoices_dir / "a.pdf").write_bytes(b"A")
    (invoices_dir / "nested" / "b.pdf").write_bytes(b"B")
    # duplicate content, should not create new entry
    (invoices_dir / "dup.pdf").write_bytes(b"A")
    # skipped directories
    (invoices_dir / "_tmp" / "skip.pdf").write_bytes(b"C")
    (invoices_dir / "quarantine" / "skip.pdf").write_bytes(b"D")

    index = GMAIL.load_existing_hash_index(str(invoices_dir))
    assert len(index) == 2
    digest_a = hashlib.sha256(b"A").hexdigest()
    digest_b = hashlib.sha256(b"B").hexdigest()
    assert digest_a in index and Path(index[digest_a]).name in {"a.pdf", "dup.pdf"}
    assert digest_b in index and Path(index[digest_b]).name == "b.pdf"
