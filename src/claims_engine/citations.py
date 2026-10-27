"""Citation validation: every cited passage must be real, in scope, and exactly as retrieved.

An EvidenceRef is accepted only if ALL hold:
  * its chunk_id was retrieved in THIS request (and was not quarantined);
  * doc_id, doc_sha256, doc_version, page_number and clause_id equal the retrieved chunk's;
  * its document is inside the request's allowed scope and in the registry with the same
    version and hash;
  * its quote is a verbatim (whitespace-normalised) substring of the chunk text.
Anything else (fabricated, missing, mismatched, out-of-scope) is an error.
"""
from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass

from .schemas import Assessment, AssessmentStatus, Chunk, EvidenceRef


@dataclass(frozen=True)
class DocInfo:
    doc_id: str
    filename: str
    version: str
    sha256: str


@dataclass(frozen=True)
class CitationError:
    code: str
    chunk_id: str
    detail: str = ""

    def __str__(self) -> str:
        return f"{self.code}:{self.chunk_id}" + (f" ({self.detail})" if self.detail else "")


def _norm(s: str) -> str:
    return " ".join(s.split())


def check_ref(ref: EvidenceRef, retrieved: Mapping[str, Chunk], allowed: Collection[str],
              registry: Mapping[str, DocInfo]) -> list[CitationError]:
    cid = ref.chunk_id
    chunk = retrieved.get(cid)
    if chunk is None:
        return [CitationError("unknown_chunk", cid, "not among this request's retrieved evidence")]
    errs: list[CitationError] = []
    if ref.doc_id not in allowed:
        errs.append(CitationError("out_of_scope", cid, ref.doc_id))
    if ref.doc_id != chunk.doc_id:
        errs.append(CitationError("doc_id_mismatch", cid))
    if ref.doc_sha256 != chunk.doc_sha256:
        errs.append(CitationError("doc_hash_mismatch", cid))
    if ref.doc_version is None:
        errs.append(CitationError("missing_version", cid))
    elif ref.doc_version != chunk.doc_version:
        errs.append(CitationError("version_mismatch", cid))
    if ref.page_number != chunk.page_number:
        errs.append(CitationError("page_mismatch", cid, f"{ref.page_number} != {chunk.page_number}"))
    if ref.clause_id != chunk.clause_id:
        errs.append(CitationError("clause_mismatch", cid, f"{ref.clause_id} != {chunk.clause_id}"))
    if _norm(ref.quote) not in _norm(chunk.text):
        errs.append(CitationError("quote_mismatch", cid))
    info = registry.get(ref.doc_id)
    if info is None:
        errs.append(CitationError("unregistered_document", cid))
    elif info.version != chunk.doc_version or info.sha256 != chunk.doc_sha256:
        errs.append(CitationError("registry_mismatch", cid))
    return errs


def validate_citations(a: Assessment, retrieved: Mapping[str, Chunk], allowed: Collection[str],
                       registry: Mapping[str, DocInfo]) -> list[CitationError]:
    errs: list[CitationError] = []
    refs = (*a.supporting_clauses, *a.exclusions_and_limitations)
    if a.status == AssessmentStatus.POTENTIALLY_COVERED and not a.supporting_clauses:
        errs.append(CitationError("no_citation", "-", "coverage verdict without supporting clause"))
    if a.status == AssessmentStatus.POTENTIALLY_EXCLUDED and not a.exclusions_and_limitations:
        errs.append(CitationError("no_citation", "-", "exclusion verdict without exclusion clause"))
    for r in refs:
        errs.extend(check_ref(r, retrieved, allowed, registry))
    return errs