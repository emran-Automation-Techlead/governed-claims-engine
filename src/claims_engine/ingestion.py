"""Secure PDF ingestion with page-level provenance.

Uploaded files are untrusted. We never execute or render anything: we only validate the
bytes, open them with PyMuPDF from memory, and read plain text per page.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import fitz  # PyMuPDF

from .config import IngestionLimits
from .schemas import DocumentRecord, PageStatus, PageText

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WS = re.compile(r"[ \t]+")


class IngestionError(Exception):
    """Raised for any rejected input. `code` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean(text: str) -> str:
    text = _CONTROL.sub("", text)
    lines = [_WS.sub(" ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def ingest_pdf_bytes(
    data: bytes,
    filename: str,
    *,
    version: str = "1",
    limits: IngestionLimits | None = None,
) -> DocumentRecord:
    limits = limits or IngestionLimits()
    safe_name = Path(filename).name  # strip any directory component
    if not safe_name.lower().endswith(".pdf"):
        raise IngestionError("bad_extension", "only .pdf files are accepted")
    if len(data) == 0:
        raise IngestionError("empty_file", "file is empty")
    if len(data) > limits.max_file_bytes:
        raise IngestionError("too_large", f"file exceeds {limits.max_file_bytes} bytes")
    if b"%PDF-" not in data[:1024]:  # the PDF spec allows the header within the first 1 KiB
        raise IngestionError("bad_magic", "content is not a PDF (missing %PDF- header)")

    digest = sha256_hex(data)
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises several exception types
        raise IngestionError("malformed_pdf", f"cannot open PDF: {type(exc).__name__}") from exc

    try:
        if doc.needs_pass or doc.is_encrypted:
            raise IngestionError("encrypted", "encrypted PDFs are not accepted")
        n = doc.page_count
        if n < 1:
            raise IngestionError("no_pages", "PDF has no pages")
        if n > limits.max_pages:
            raise IngestionError("too_many_pages", f"{n} pages exceeds limit {limits.max_pages}")

        pages: list[PageText] = []
        for i in range(n):
            try:
                raw = doc[i].get_text("text")
            except Exception as exc:
                raise IngestionError(
                    "page_extract_failed", f"page {i + 1}: {type(exc).__name__}"
                ) from exc
            text = _clean(raw)
            status = PageStatus.OK if len(text) >= limits.min_page_chars else PageStatus.EMPTY
            pages.append(
                PageText(page_number=i + 1, text=text, char_count=len(text), status=status)
            )
    finally:
        doc.close()

    ok = sum(p.status == PageStatus.OK for p in pages)
    if ok == 0:
        raise IngestionError("no_text", "no extractable text (scanned or image-only PDF?)")
    if ok / len(pages) < limits.min_ok_page_ratio:
        raise IngestionError("poor_extraction", f"only {ok}/{len(pages)} pages have usable text")

    empty = [p.page_number for p in pages if p.status == PageStatus.EMPTY]
    warnings = (f"empty pages (excluded from retrieval): {empty}",) if empty else ()
    return DocumentRecord(
        doc_id=f"doc-{digest[:12]}",
        filename=safe_name,
        version=version,
        sha256=digest,
        size_bytes=len(data),
        page_count=n,
        pages=tuple(pages),
        warnings=warnings,
    )


def ingest_pdf_path(path: str | Path, *, version: str = "1",
                    limits: IngestionLimits | None = None) -> DocumentRecord:
    p = Path(path)
    limits = limits or IngestionLimits()
    try:
        size = p.stat().st_size
    except OSError as exc:
        raise IngestionError("unreadable", f"cannot stat file: {type(exc).__name__}") from exc
    if size > limits.max_file_bytes:  # reject before reading into memory
        raise IngestionError("too_large", f"file exceeds {limits.max_file_bytes} bytes")
    return ingest_pdf_bytes(p.read_bytes(), p.name, version=version, limits=limits)

