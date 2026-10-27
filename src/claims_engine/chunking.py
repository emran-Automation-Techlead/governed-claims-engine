r"""Page- and clause-aware chunking.

Policy text is split at clause boundaries ("3.2 Gradual Leakage ..."), never mid-clause, so an
exclusion keeps its conditions and exceptions. Each chunk lies on one page (exact provenance).

Rules
* Running headers/footers (a line repeating on >= 60 % of pages, digits ignored; needs >= 3 pages)
  are removed so "Page 3 of 5" never pollutes retrieval.
* "N. Title" starts a section; "N.M Text" starts a clause. The section title is prepended to the
  indexed text so a clause is retrievable by its topic ("Exclusions", "Water Damage").
* A clause continuing onto the next page becomes a second chunk with continues_previous=True.
* A clause longer than `max_chars` is split on sentence boundaries with a one-sentence overlap.
* Chunk ids are deterministic: <doc_id>:p<page>:<clause|sec<N>|pre>[:s<k>].
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .schemas import Chunk, DocumentRecord, PageStatus

_SUB = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,3})\.?\s+(\S.*)$")
_SEC = re.compile(r"^(\d{1,2})\.\s+(\S.*)$")
_OPENERS = "'\u2018\"\u00ab\u201e("
_SENT = re.compile(r"(?<=[.;!?])\s+")
_DIGITS = re.compile(r"\d+")


def _starts_like_heading(rest: str) -> bool:
    return rest[0].isupper() or rest[0] in _OPENERS


@dataclass
class _Seg:
    page: int
    clause: str | None
    section: str | None
    section_title: str | None
    lines: list[str] = field(default_factory=list)
    continuation: bool = False
    has_body: bool = False  # False for a bare section heading (it only supplies context)


def _running_lines(doc: DocumentRecord) -> set[str]:
    pages = [p for p in doc.pages if p.status == PageStatus.OK]
    if len(pages) < 3:
        return set()
    seen: dict[str, int] = {}
    for p in pages:
        for norm in {_DIGITS.sub("#", ln.lower()) for ln in p.text.splitlines()}:
            seen[norm] = seen.get(norm, 0) + 1
    need = math.ceil(0.6 * len(pages))
    return {n for n, c in seen.items() if c >= need}


def _split_long(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sents = [s for s in _SENT.split(text) if s]
    parts: list[str] = []
    cur: list[str] = []
    for s in sents:
        if cur and len(" ".join(cur + [s])) > max_chars:
            parts.append(" ".join(cur))
            cur = [cur[-1], s]  # one-sentence overlap keeps conditions next to what they qualify
        else:
            cur.append(s)
    if cur:
        parts.append(" ".join(cur))
    return parts


def chunk_document(doc: DocumentRecord, *, max_chars: int = 1200) -> tuple[Chunk, ...]:
    running = _running_lines(doc)
    segs: list[_Seg] = []
    cur: _Seg | None = None
    section: str | None = None
    section_title: str | None = None

    for page in doc.pages:
        if page.status != PageStatus.OK:
            continue
        if cur is not None and cur.page != page.page_number:
            segs.append(cur)
            cur = _Seg(page.page_number, cur.clause, cur.section, cur.section_title,
                       continuation=True)
        for line in page.text.splitlines():
            if _DIGITS.sub("#", line.lower()) in running:
                continue
            sub, sec = _SUB.match(line), _SEC.match(line)
            if sub and _starts_like_heading(sub.group(2)):
                if cur is not None:
                    segs.append(cur)
                cur = _Seg(page.page_number, sub.group(1), section, section_title, [line],
                           has_body=True)
            elif sec and _starts_like_heading(sec.group(2)) and len(line) <= 80:
                if cur is not None:
                    segs.append(cur)
                section, section_title = sec.group(1), sec.group(2).strip().rstrip(".")
                cur = _Seg(page.page_number, None, section, section_title, [line])
            else:
                if cur is None:
                    cur = _Seg(page.page_number, None, None, None)
                cur.lines.append(line)
                cur.has_body = True
        # the current segment may continue on the next page; flushed lazily above
    if cur is not None:
        segs.append(cur)

    chunks: list[Chunk] = []
    used: set[str] = set()
    for seg in segs:
        if not seg.has_body:
            continue
        label = seg.clause or (f"sec{seg.section}" if seg.section else "pre")
        for k, part in enumerate(_split_long(" ".join(seg.lines), max_chars)):
            cid = f"{doc.doc_id}:p{seg.page}:{label}" + (f":s{k}" if k else "")
            n = 1
            while cid in used:  # defensive: duplicate labels on one page
                n += 1
                cid = f"{doc.doc_id}:p{seg.page}:{label}~{n}"
            used.add(cid)
            ctx = f"{seg.section_title}. " if seg.section_title else ""
            chunks.append(Chunk(
                chunk_id=cid, doc_id=doc.doc_id, doc_sha256=doc.sha256, doc_version=doc.version,
                filename=doc.filename, page_number=seg.page, clause_id=seg.clause,
                section_id=seg.section, section_title=seg.section_title, text=part,
                index_text=ctx + part, continues_previous=seg.continuation or k > 0))
    linked: list[Chunk] = []
    for i, c in enumerate(chunks):
        linked.append(c.model_copy(update={
            "prev_chunk_id": chunks[i - 1].chunk_id if i else None,
            "next_chunk_id": chunks[i + 1].chunk_id if i + 1 < len(chunks) else None}))
    return tuple(linked)