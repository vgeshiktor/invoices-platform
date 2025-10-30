import importlib.util
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


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
    # Playwright (heavy dep) – provide no-op placeholders
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

    # MSAL – stub PublicClientApplication
    msal_mod = _ensure_module("msal")

    class DummyPCA:
        def __init__(self, *args, **kwargs):
            pass

        def initiate_device_flow(self, *args, **kwargs):
            raise RuntimeError("msal stub: not available in tests")

        def acquire_token_by_device_flow(self, *args, **kwargs):
            raise RuntimeError("msal stub: not available in tests")

    msal_mod.PublicClientApplication = DummyPCA  # type: ignore[attr-defined]

    # Google API clients – supply minimal placeholders so import succeeds
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


def _load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {name} from {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GRAPH = _load_module("graph_invoice_finder", "graph_invoice_finder.v3.9.2.py")
GMAIL = _load_module("gmail_invoice_finder", "gmail_invoice_finder.v1.0.py")


def test_graph_should_consider_message_positive_keyword():
    assert GRAPH.should_consider_message("חשבונית מס קבלה", "")
    assert GRAPH.should_consider_message("Invoice for services", "")


def test_graph_should_consider_message_reject_negative_hint():
    assert not GRAPH.should_consider_message("תלוש שכר יוני", "")
    assert not GRAPH.should_consider_message("Salary payment", "")


def test_graph_sanitize_filename_and_unique(tmp_path):
    base_dir = tmp_path / "out"
    base_dir.mkdir()

    first = GRAPH.ensure_unique_path(str(base_dir), "חשבונית:2025/06.pdf")
    Path(first).write_bytes(b"pdf")
    second = GRAPH.ensure_unique_path(str(base_dir), "חשבונית:2025/06.pdf")

    assert first.endswith("חשבונית_2025_06.pdf")
    assert second.endswith("__2.pdf")


def test_graph_pdf_confidence_ratio():
    stats = {"pos_hits": 2, "neg_hits": 1}
    assert pytest.approx(GRAPH.pdf_confidence(stats)) == pytest.approx(2 / 3)
    stats = {"pos_hits": 0, "neg_hits": 0}
    assert GRAPH.pdf_confidence(stats) == 0.0


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


def test_gmail_extract_links_deduplicates_and_captures(tmp_path):
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
