"""Entfernt zitierten Text, damit nur der neu geschriebene Teil einer Mail bewertet wird."""

import re
from html.parser import HTMLParser

# Elemente, deren Inhalt komplett ein Zitat oder eine Signatur ist
_SKIP_CLASSES = {"gmail_quote", "moz-cite-prefix", "moz-signature", "gmail_signature"}
_SKIP_IDS = {"_rc_sig"}
# Ab diesen Markern folgt bis zum Ende nur noch die zitierte Mail (Outlook im Web)
_CUT_IDS = {"divRplyFwdMsg", "appendonsend"}

_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
_BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "hr", "table"}

_QUOTE_HEADERS = [
    re.compile(r"^\s*am .{3,160} schrieb .{0,160}:\s*$", re.IGNORECASE),
    re.compile(r"^\s*on .{3,160} wrote:\s*$", re.IGNORECASE),
    re.compile(
        r"^\s*-{2,}\s*(weitergeleitete nachricht|forwarded message|original message|"
        r"urspr(ü|ue)ngliche nachricht|original-nachricht)\s*-{2,}\s*$",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*_{10,}\s*$"),
]
_OUTLOOK_FROM = re.compile(r"^\s*\*?(von|from):\*?\s", re.IGNORECASE)
_OUTLOOK_FIELDS = re.compile(r"^\s*\*?(gesendet|sent|datum|date|an|to|betreff|subject):\*?\s", re.IGNORECASE)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[str] = []
        self.skip_depth: int | None = None
        self.cut = False

    def _skips(self, tag: str, attrs: dict) -> bool:
        if tag in ("script", "style", "head", "title"):
            return True
        if tag == "blockquote":
            return True
        classes = set((attrs.get("class") or "").split())
        return bool(classes & _SKIP_CLASSES) or attrs.get("id") in _SKIP_IDS

    def handle_starttag(self, tag, attrs):
        if self.cut:
            return
        attrs = dict(attrs)
        if attrs.get("id") in _CUT_IDS:
            self.cut = True
            return
        if tag in _BLOCK and self.skip_depth is None:
            self.parts.append("\n")
        if tag in _VOID:
            return
        self.stack.append(tag)
        if self.skip_depth is None and self._skips(tag, attrs):
            self.skip_depth = len(self.stack)

    def handle_endtag(self, tag):
        if self.cut or tag in _VOID or tag not in self.stack:
            return
        while self.stack:
            if self.stack.pop() == tag:
                break
        if self.skip_depth is not None and len(self.stack) < self.skip_depth:
            self.skip_depth = None
        if tag in _BLOCK and self.skip_depth is None:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.cut and self.skip_depth is None:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    """HTML in Text umwandeln und dabei zitierte Blöcke weglassen."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    text = "".join(parser.parts).replace("\xa0", " ")
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _is_outlook_header(lines: list[str], i: int) -> bool:
    """'Von: …' gefolgt von 'Gesendet:'/'An:'/'Betreff:' innerhalb von 4 Zeilen."""
    if not _OUTLOOK_FROM.match(lines[i]):
        return False
    return any(_OUTLOOK_FIELDS.match(line) for line in lines[i + 1 : i + 5])


def strip_plain_quotes(text: str) -> str:
    lines = text.splitlines()
    kept = []
    for i, line in enumerate(lines):
        if any(p.match(line) for p in _QUOTE_HEADERS) or _is_outlook_header(lines, i):
            break
        if line.lstrip().startswith(">"):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def strip_quotes(text: str, html: str | None = None) -> str:
    """Neu geschriebener Teil einer Mail. HTML wird bevorzugt, wenn vorhanden."""
    if html and html.strip():
        text = html_to_text(html)
    return strip_plain_quotes(text or "")
