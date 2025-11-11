import sys
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "apps" / "workers-py" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from invplatform.adapters import base  # noqa: E402
from invplatform.usecases import fetch_invoices as fetch_uc  # noqa: E402


def test_attachment_meta_defaults():
    meta = base.AttachmentMeta(
        id="1", name="invoice.pdf", content_type="application/pdf"
    )
    assert meta.size is None
    assert meta.name.endswith(".pdf")


def test_message_meta_defaults():
    msg = base.MessageMeta(
        id="m1",
        subject="Invoice",
        sender="sender@example.com",
        received="2025-01-01T00:00:00Z",
    )
    assert msg.preview == ""
    assert msg.has_attachments is False
    assert msg.web_link is None


class DummyAdapter:
    def __init__(self, messages: Iterable[base.MessageMeta]):
        self._messages = list(messages)

    def iter_messages(self):
        return self._messages

    def iter_attachments(self, message):
        return [
            base.AttachmentMeta(
                id=f"{message.id}-att",
                name="invoice.pdf",
                content_type="application/pdf",
                size=100,
            )
        ]

    def download_attachment(self, message, attachment):
        return f"{message.id}:{attachment.id}".encode()


def test_fetch_invoices_placeholder_returns_empty(monkeypatch):
    adapter = DummyAdapter(
        [
            base.MessageMeta(
                id="m1",
                subject="Invoice",
                sender="sender@example.com",
                received="2025-01-01T00:00:00Z",
            )
        ]
    )
    config = fetch_uc.FetchConfig(start_date="2025-01-01", end_date="2025-02-01")
    result = fetch_uc.fetch_invoices(adapter, config)
    assert result == []
