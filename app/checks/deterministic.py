"""Deterministic document extraction and intake checks."""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import PurePath
from xml.etree import ElementTree

from docx import Document as DocxDocument
from docx.opc.exceptions import PackageNotFoundError
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.database.models import ChecklistItemInstance, Engagement

DATE_PATTERNS = (
    (re.compile(r"\b(20\d{2}-\d{1,2}-\d{1,2})\b"), ("%Y-%m-%d",)),
    (re.compile(r"\b(\d{1,2}/\d{1,2}/(?:20)?\d{2})\b"), ("%m/%d/%Y", "%m/%d/%y")),
)
SAR_PATTERNS = (
    re.compile(r"\bsuspicious activity reports?\b", re.IGNORECASE),
    re.compile(r"\bSARs?\b", re.IGNORECASE),
    re.compile(r"\bFinCEN\s+(?:Form\s+)?111\b", re.IGNORECASE),
    re.compile(r"\bSAR narrative\b", re.IGNORECASE),
)
SIGNATURE_PATTERNS = (
    re.compile(r"\belectronically signed\b", re.IGNORECASE),
    re.compile(r"\bsigned by\b", re.IGNORECASE),
    re.compile(r"\bsignature\s*:", re.IGNORECASE),
    re.compile(r"(?:^|\s)/s/(?:\s|$)", re.IGNORECASE),
)


@dataclass
class ExtractedDocument:
    pages: list[str]
    readable: bool
    extractable: bool
    has_signature: bool = False
    error_code: str | None = None

    @property
    def text(self) -> str:
        return "\n".join(self.pages)


@dataclass
class DeterministicCheck:
    check_type: str
    status: str
    client_reason: str | None = None
    details: dict[str, object] = field(default_factory=dict)


@dataclass
class DeterministicReport:
    extracted: ExtractedDocument
    checks: list[DeterministicCheck]
    blocking_reason_code: str | None = None
    requires_manual_review: bool = False


def _pdf(content: bytes) -> ExtractedDocument:
    reader = PdfReader(io.BytesIO(content))
    if reader.is_encrypted:
        return ExtractedDocument([], False, False, error_code="encrypted_pdf")
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    fields = reader.get_fields() or {}
    has_signature = any(str(field.get("/FT", "")) == "/Sig" for field in fields.values())
    return ExtractedDocument(pages, bool(pages), True, has_signature)


def _docx(content: bytes) -> ExtractedDocument:
    document = DocxDocument(io.BytesIO(content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs).strip()
    return ExtractedDocument([text], True, True)


def _xlsx(content: bytes) -> ExtractedDocument:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = [
            name
            for name in archive.namelist()
            if name == "xl/sharedStrings.xml" or name.startswith("xl/worksheets/sheet")
        ]
        text = "\n".join(
            " ".join(ElementTree.fromstring(archive.read(name)).itertext()) for name in names
        )
    return ExtractedDocument([text.strip()], True, True)


def _image(content: bytes) -> ExtractedDocument:
    with Image.open(io.BytesIO(content)) as image:
        image.verify()
    return ExtractedDocument([""], True, False)


def extract_document(filename: str, content: bytes) -> ExtractedDocument:
    suffix = PurePath(filename).suffix.casefold()
    try:
        if suffix == ".pdf":
            extracted = _pdf(content)
        elif suffix == ".docx":
            extracted = _docx(content)
        elif suffix == ".xlsx":
            extracted = _xlsx(content)
        elif suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            extracted = _image(content)
        elif suffix in {".txt", ".csv"}:
            extracted = ExtractedDocument([content.decode("utf-8")], True, True)
        elif suffix in {".doc", ".xls"}:
            extracted = ExtractedDocument([""], True, False)
        else:
            return ExtractedDocument([], False, False, error_code="unsupported_type")
    except (
        ElementTree.ParseError,
        OSError,
        PackageNotFoundError,
        PyPdfError,
        UnicodeError,
        UnidentifiedImageError,
        ValueError,
        zipfile.BadZipFile,
    ):
        return ExtractedDocument([], False, False, error_code="unreadable")
    extracted.has_signature = extracted.has_signature or any(
        pattern.search(extracted.text) for pattern in SIGNATURE_PATTERNS
    )
    return extracted


def contains_sar_indicator(filename: str, extracted: ExtractedDocument) -> bool:
    sample = f"{filename}\n{extracted.text}"
    return any(pattern.search(sample) for pattern in SAR_PATTERNS)


def _dates(text: str) -> list[date]:
    found: list[date] = []
    for pattern, formats in DATE_PATTERNS:
        for match in pattern.findall(text):
            for date_format in formats:
                try:
                    found.append(datetime.strptime(match, date_format).date())
                    break
                except ValueError:
                    continue
    return found


def run_deterministic_checks(
    *,
    item: ChecklistItemInstance,
    engagement: Engagement,
    filename: str,
    content: bytes,
) -> DeterministicReport:
    extracted = extract_document(filename, content)
    checks: list[DeterministicCheck] = []
    if not extracted.readable:
        checks.append(
            DeterministicCheck(
                "readable",
                "failed",
                "The file could not be read. Please upload a clear, unencrypted copy.",
                {"error_code": extracted.error_code},
            )
        )
        return DeterministicReport(extracted, checks, blocking_reason_code="unreadable")
    checks.append(DeterministicCheck("readable", "passed"))

    page_count = len(extracted.pages)
    if page_count < item.min_pages:
        checks.append(
            DeterministicCheck(
                "page_count",
                "failed",
                "The file appears to be missing pages. Please upload the complete document.",
                {"page_count": page_count, "minimum": item.min_pages},
            )
        )
        return DeterministicReport(extracted, checks, blocking_reason_code="missing_pages")
    checks.append(DeterministicCheck("page_count", "passed", details={"page_count": page_count}))

    if item.review_period_rule:
        dates = _dates(extracted.text)
        in_period = any(
            engagement.review_period_start <= value <= engagement.review_period_end
            for value in dates
        )
        if not in_period:
            checks.append(
                DeterministicCheck(
                    "review_period",
                    "failed",
                    "The file does not show a date within the requested review period.",
                    {"dates_found": len(dates)},
                )
            )
            return DeterministicReport(extracted, checks, blocking_reason_code="wrong_period")
        checks.append(DeterministicCheck("review_period", "passed"))

    if item.requires_signature:
        if not extracted.has_signature:
            checks.append(
                DeterministicCheck(
                    "signature",
                    "failed",
                    "A required signature could not be found. Please upload the signed document.",
                )
            )
            return DeterministicReport(extracted, checks, blocking_reason_code="missing_pages")
        checks.append(DeterministicCheck("signature", "passed"))

    return DeterministicReport(
        extracted,
        checks,
        requires_manual_review=not extracted.extractable,
    )
