"""Next-page discovery for listing pages (deterministic, no LLM).

Traversal goes *down* from a listing into its detail pages; pagination goes
*across* to page 2, 3, ... of the same listing. Without it a seed yields only
whatever happens to sit on page one, no matter how high the traversal cap.

Deterministic on purpose: `rel="next"` is an unambiguous machine-readable
declaration, so there is no judgment for an LLM to add. Link *text* ("Next",
"older posts") is not consulted -- it is ambiguous enough to walk a run into
the wrong part of a site, and a missed page is much cheaper than a wrong one.
"""
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

#: listing pages fetched per seed, including the seed page itself
DEFAULT_MAX_PAGES = 1


class _NextLinkFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.href is not None or tag not in ("a", "link"):
            return
        attr = dict(attrs)
        rel = attr.get("rel") or ""
        if "next" in re.split(r"\s+", rel.strip().lower()) and attr.get("href"):
            self.href = attr["href"]

    # <link rel="next"> is void; HTMLParser reports it here when self-closed
    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def next_page_url(raw_html: str, page_url: str) -> str | None:
    """The URL of the next listing page, or None if the page declares no next."""
    finder = _NextLinkFinder()
    finder.feed(raw_html)
    finder.close()
    if finder.href is None:
        return None

    resolved = urljoin(page_url, finder.href)
    return resolved if resolved != page_url else None
