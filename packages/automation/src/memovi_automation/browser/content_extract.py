"""HTML content extraction helpers for structured browser results."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self._in_title = False
        self._skip_depth = 0
        self.meta: dict[str, str] = {}
        self.links: list[dict[str, str]] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): (value or "") for key, value in attrs}
        lowered = tag.lower()

        if lowered in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        if lowered == "title":
            self._in_title = True
            return

        if lowered == "meta":
            name = attr_map.get("name") or attr_map.get("property") or attr_map.get("http-equiv")
            content = attr_map.get("content", "").strip()
            if name and content:
                self.meta[name.strip().lower()] = content
            return

        if lowered == "a":
            href = attr_map.get("href", "").strip()
            if href:
                self.links.append({"href": href, "text": ""})
            return

        if lowered in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if lowered == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
            return
        if self.links and self.links[-1]["text"] == "":
            # Prefer first text node for the most recent anchor.
            self.links[-1]["text"] = text[:200]
        self.text_parts.append(text + " ")


_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def extract_page_content(html: str, *, base_url: str) -> dict[str, object]:
    """Extract title, readable text, links, and metadata from HTML."""
    parser = _PageParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Malformed HTML still yields whatever was parsed.
        pass

    title = " ".join(parser.title_parts).strip()
    readable = _normalize_text("".join(parser.text_parts))
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for link in parser.links:
        absolute = urljoin(base_url, link["href"])
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append({"href": absolute, "text": link["text"].strip()})

    return {
        "title": title,
        "readable_text": readable,
        "links": links,
        "metadata": dict(parser.meta),
    }


def _normalize_text(text: str) -> str:
    cleaned = _WHITESPACE_RE.sub(" ", text)
    cleaned = _BLANK_LINES_RE.sub("\n\n", cleaned.replace(" \n", "\n"))
    return cleaned.strip()
