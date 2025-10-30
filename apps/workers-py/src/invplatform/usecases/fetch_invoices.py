from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..adapters.base import MailAdapter, MessageMeta


@dataclass
class FetchConfig:
    start_date: str
    end_date: str
    verify: bool = False
    exclude_sent: bool = True


def fetch_invoices(adapter: MailAdapter, config: FetchConfig) -> List[MessageMeta]:
    """Placeholder orchestration that will call the adapter in future iterations."""
    return []
