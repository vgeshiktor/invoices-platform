from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Protocol


@dataclass
class AttachmentMeta:
    id: str
    name: str
    content_type: str
    size: Optional[int] = None


@dataclass
class MessageMeta:
    id: str
    subject: str
    sender: str
    received: str
    web_link: Optional[str] = None
    preview: str = ""
    has_attachments: bool = False


class MailAdapter(Protocol):
    """Minimal contract future adapters should fulfil."""

    def iter_messages(self) -> Iterable[MessageMeta]: ...

    def iter_attachments(self, message: MessageMeta) -> Iterable[AttachmentMeta]: ...

    def download_attachment(self, message: MessageMeta, attachment: AttachmentMeta) -> bytes: ...
