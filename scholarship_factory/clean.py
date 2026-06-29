import re
from html.parser import HTMLParser

_SKIP_TAGS = {"script", "style"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._ldjson_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            attr_dict = dict(attrs)
            if tag == "script" and attr_dict.get("type") == "application/ld+json":
                self._ldjson_depth += 1
            else:
                self._skip_depth += 1
        elif tag == "time":
            datetime_attr = dict(attrs).get("datetime")
            if datetime_attr:
                self._chunks.append(datetime_attr)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._ldjson_depth > 0:
            self._ldjson_depth -= 1
        elif tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        self._chunks.append(data)

    def text(self) -> str:
        return "".join(self._chunks)


def clean_html(raw_html: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(raw_html)
    extractor.close()
    text = extractor.text()
    return re.sub(r"\s+", " ", text).strip()
