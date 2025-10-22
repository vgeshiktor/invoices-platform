"""Utility to download invoice PDF from a Bezeq invoice landing page.

The script tries to be resilient by inspecting the HTML for PDF links in
several common places (``href``/``src`` attributes as well as raw script
content).  Once a PDF URL is found it is downloaded using ``requests``.

Usage::

    python -m workers.download_invoice \
        "https://myinvoice.bezeq.co.il/?MailID=..." \
        --output invoice.pdf

By default the first discovered PDF is downloaded.  Use ``--list`` to see all
candidates, or ``--index`` to choose a specific one.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable, Sequence
from urllib.parse import urljoin

import requests


@dataclass
class Candidate:
    """Represents a PDF download candidate discovered on the page."""

    url: str
    source: str


class _PDFLinkParser(HTMLParser):
    """Lightweight HTML parser that extracts links to PDF resources."""

    def __init__(self) -> None:
        super().__init__()
        self._candidates: list[Candidate] = []

    @staticmethod
    def _is_pdf(value: str | None) -> bool:
        return bool(value) and ".pdf" in value.lower()

    def _add_candidate(self, raw_url: str | None, *, attr: str, tag: str) -> None:
        if self._is_pdf(raw_url):
            self._candidates.append(Candidate(raw_url, f"<{tag} {attr}>"))

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, str]]) -> None:  # type: ignore[override]
        attr_map = dict(attrs)

        if tag == "param":
            # <param name="src" value="file.pdf">
            name = attr_map.get("name", "").lower()
            if name in {"src", "href"}:
                self._add_candidate(attr_map.get("value"), attr="value", tag=tag)

        for attribute in ("href", "src", "data", "data-src", "data-href"):
            self._add_candidate(attr_map.get(attribute), attr=attribute, tag=tag)

    def candidates(self) -> list[Candidate]:
        return list(self._candidates)


def _find_pdf_urls(html: str) -> list[Candidate]:
    parser = _PDFLinkParser()
    parser.feed(html)
    candidates = parser.candidates()

    # Inspect raw HTML for URLs that are embedded inside JavaScript.
    for match in re.findall(
        r"https?://[^'\"\s>]+\.pdf[^'\"\s>]*", html, flags=re.IGNORECASE
    ):
        candidates.append(Candidate(match, "inline-script"))

    return candidates


def _normalise_candidates(
    candidates: Iterable[Candidate], base_url: str
) -> list[Candidate]:
    normalised: list[Candidate] = []
    for candidate in candidates:
        absolute_url = urljoin(base_url, candidate.url)
        normalised.append(Candidate(absolute_url, candidate.source))
    return normalised


def download_pdf(
    url: str, *, output: pathlib.Path, session: requests.Session | None = None
) -> pathlib.Path:
    """Download ``url`` into ``output``.

    Parameters
    ----------
    url:
        Direct PDF URL.
    output:
        Destination file path.  Intermediate directories are created
        automatically.
    session:
        Optional ``requests.Session`` to reuse HTTP settings.
    """

    sess = session or requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) PythonInvoiceDownloader/1.0",
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
    }

    response = sess.get(url, headers=headers, stream=True, timeout=30)
    response.raise_for_status()

    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("wb") as fh:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                fh.write(chunk)

    return output


def fetch_html(
    url: str, *, session: requests.Session | None = None, disable_proxy: bool = False
) -> str:
    """Fetch the HTML content for ``url`` and return it as a string."""

    sess = session or requests.Session()
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
    proxies = {} if disable_proxy else None
    response = sess.get(url, headers=headers, timeout=30, proxies=proxies)
    response.raise_for_status()
    return response.text


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Landing page that contains the invoice viewer")
    parser.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("invoice.pdf"),
        help="Destination file path (default: %(default)s)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Only list discovered PDF URLs without downloading",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=0,
        help="Index of the PDF to download when multiple links are found",
    )
    parser.add_argument(
        "--disable-proxy",
        action="store_true",
        help="Ignore HTTP(S)_PROXY environment variables during the download",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    session = requests.Session()
    if args.disable_proxy:
        session.trust_env = False

    try:
        html = fetch_html(args.url, session=session, disable_proxy=args.disable_proxy)
    except (
        requests.RequestException
    ) as exc:  # pragma: no cover - network failures are environment dependent
        print(f"Failed to fetch landing page: {exc}", file=sys.stderr)
        return 1

    candidates = _normalise_candidates(_find_pdf_urls(html), args.url)

    if not candidates:
        print("No PDF links found on the page.", file=sys.stderr)
        return 2

    if args.list:
        for idx, candidate in enumerate(candidates):
            print(f"[{idx}] {candidate.url} (found in {candidate.source})")
        return 0

    index = args.index
    if index < 0 or index >= len(candidates):
        print(
            f"Invalid index {index}; {len(candidates)} candidates discovered. "
            "Use --list to see all options.",
            file=sys.stderr,
        )
        return 3

    pdf_candidate = candidates[index]

    try:
        download_pdf(pdf_candidate.url, output=args.output, session=session)
    except (
        requests.RequestException
    ) as exc:  # pragma: no cover - network failures are environment dependent
        print(f"Failed to download PDF: {exc}", file=sys.stderr)
        return 4

    print(f"Downloaded {pdf_candidate.url} to {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution entry point
    sys.exit(main())
