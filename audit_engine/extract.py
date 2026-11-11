"""Text extraction from uploaded files. Every problem is a clean skip reason, never a crash.

Pages: PDFs keep real pages. Text-like files are cut into pseudo-pages of PAGE_CHARS characters so
citations still point somewhere checkable. Images and legacy Office files are not read.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

MAX_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 200
MAX_TOTAL_CHARS = 30_000  # sent to a model per file; later pages are dropped, not summarised
PAGE_CHARS = 3_000
TEXT_SUFFIXES = {".txt", ".csv"}


class ExtractionSkip(Exception):
    """File cannot be read. ``code`` maps to a message in engine.SKIP_MESSAGES."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Extracted:
    pages: list[str]
    truncated: bool

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def as_text(self) -> str:
        return "\n".join(f"[page {n}]\n{text}" for n, text in enumerate(self.pages, 1))


def _cap(pages: list[str]) -> Extracted:
    kept: list[str] = []
    total = 0
    truncated = False
    for text in pages:
        if total + len(text) > MAX_TOTAL_CHARS:
            room = MAX_TOTAL_CHARS - total
            if room > 0:
                kept.append(text[:room])
            truncated = True
            break
        kept.append(text)
        total += len(text)
    if not any(page.strip() for page in kept):
        raise ExtractionSkip("no_text")
    return Extracted(kept, truncated)


def _pseudo_pages(text: str) -> list[str]:
    return [text[i : i + PAGE_CHARS] for i in range(0, len(text), PAGE_CHARS)] or [""]


def _pdf(content: bytes) -> list[str]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise ExtractionSkip("encrypted")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ExtractionSkip("too_many_pages")
        return [(page.extract_text() or "") for page in reader.pages]
    except ExtractionSkip:
        raise
    except Exception:  # noqa: BLE001 - malformed input of any kind is a clean skip
        raise ExtractionSkip("unreadable") from None


def _docx(content: bytes) -> list[str]:
    import docx

    try:
        document = docx.Document(io.BytesIO(content))
        text = "\n".join(p.text for p in document.paragraphs)
    except Exception:  # noqa: BLE001
        raise ExtractionSkip("unreadable") from None
    return _pseudo_pages(text)


def extract(content: bytes | None, suffix: str) -> Extracted:
    suffix = suffix.casefold()
    if content is None:
        raise ExtractionSkip("storage_unavailable")
    if not content:
        raise ExtractionSkip("empty")
    if len(content) > MAX_BYTES:
        raise ExtractionSkip("too_large")
    if suffix == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ExtractionSkip("unreadable")
        return _cap(_pdf(content))
    if suffix == ".docx":
        if not content.startswith(b"PK\x03\x04"):
            raise ExtractionSkip("unreadable")
        return _cap(_docx(content))
    if suffix in TEXT_SUFFIXES:
        if b"\x00" in content[:4096]:
            raise ExtractionSkip("unreadable")
        return _cap(_pseudo_pages(content.decode("utf-8", errors="replace")))
    raise ExtractionSkip("unsupported_type")
