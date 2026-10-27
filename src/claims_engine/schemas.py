"""Pydantic schemas: documents, evidence, assessments, audit metadata, human review.

Design rules enforced here (not just documented):
* a verdict of potentially_covered / potentially_excluded MUST cite evidence;
* a non-verdict (insufficient_evidence / human_review_required) MUST say why;
* an override MUST carry a reason;
* audit records hold identifiers and hashes, never raw document or claim text.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def utcnow() -> datetime:
    return datetime.now(UTC)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PageStatus(str, Enum):
    OK = "ok"
    EMPTY = "empty"


class PageText(_Strict):
    page_number: int = Field(ge=1, description="1-based page number in the source PDF")
    text: str
    char_count: int = Field(ge=0)
    status: PageStatus


class DocumentRecord(_Strict):
    doc_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    version: str = Field(min_length=1)
    sha256: Sha256
    size_bytes: int = Field(gt=0)
    page_count: int = Field(ge=1)
    pages: tuple[PageText, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _pages_consistent(self) -> Self:
        if len(self.pages) != self.page_count:
            raise ValueError("page_count does not match number of pages")
        if [p.page_number for p in self.pages] != list(range(1, self.page_count + 1)):
            raise ValueError("pages must be numbered 1..page_count in order")
        return self


class Chunk(_Strict):
    """A retrievable passage lying on exactly ONE page, so page references are exact.

    A clause that runs across a page break becomes two chunks (same clause_id, the second
    with continues_previous=True); prev/next ids let a reader fetch the surrounding text,
    which is how exceptions and conditions that follow an exclusion stay reachable.
    """

    chunk_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    doc_sha256: Sha256
    doc_version: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    clause_id: str | None = None
    section_id: str | None = None
    section_title: str | None = None
    text: str = Field(min_length=1)
    index_text: str = Field(min_length=1, description="section title + text; what retrievers see")
    continues_previous: bool = False
    prev_chunk_id: str | None = None
    next_chunk_id: str | None = None

    @property
    def char_count(self) -> int:
        return len(self.text)

    def to_evidence(self, score: float | None = None) -> EvidenceRef:
        return EvidenceRef(doc_id=self.doc_id, doc_sha256=self.doc_sha256,
                           doc_version=self.doc_version, page_number=self.page_number, chunk_id=self.chunk_id,
                           clause_id=self.clause_id, quote=self.text[:1000], score=score)


class EvidenceRef(_Strict):
    """Pointer to a passage of a specific document version. Never free-floating."""

    doc_id: str = Field(min_length=1)
    doc_sha256: Sha256
    doc_version: str | None = None  # required by the workflow citation validator
    page_number: int = Field(ge=1)
    chunk_id: str = Field(min_length=1)
    clause_id: str | None = None
    quote: str = Field(min_length=1, max_length=1000)
    score: float | None = None


class AssessmentStatus(str, Enum):
    POTENTIALLY_COVERED = "potentially_covered"
    POTENTIALLY_EXCLUDED = "potentially_excluded"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    OVERRIDDEN = "overridden"


class Assessment(_Strict):
    """Preliminary interpretation. NOT a binding claim decision."""

    status: AssessmentStatus
    summary: str = Field(min_length=1)
    supporting_clauses: tuple[EvidenceRef, ...] = ()
    exclusions_and_limitations: tuple[EvidenceRef, ...] = ()
    missing_information: tuple[str, ...] = ()
    uncertainty: str | None = None
    escalation_reason: str | None = None
    model_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    review_status: ReviewStatus = ReviewStatus.PENDING
    disclaimer: str = "Preliminary interpretation for human review; not a binding claim decision."

    @model_validator(mode="after")
    def _rules(self) -> Self:
        s = self.status
        if s == AssessmentStatus.POTENTIALLY_COVERED and not self.supporting_clauses:
            raise ValueError("potentially_covered requires supporting_clauses")
        if s == AssessmentStatus.POTENTIALLY_EXCLUDED and not self.exclusions_and_limitations:
            raise ValueError("potentially_excluded requires exclusions_and_limitations")
        if s == AssessmentStatus.INSUFFICIENT_EVIDENCE and not self.missing_information:
            raise ValueError("insufficient_evidence requires missing_information")
        if s == AssessmentStatus.HUMAN_REVIEW_REQUIRED and not self.escalation_reason:
            raise ValueError("human_review_required requires escalation_reason")
        return self


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    OVERRIDE = "override"


class HumanReview(_Strict):
    trace_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    action: ReviewAction
    override_status: AssessmentStatus | None = None
    reason: str | None = None
    timestamp: datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if self.action == ReviewAction.OVERRIDE:
            if not self.reason or not self.reason.strip():
                raise ValueError("override requires a non-empty reason")
            if self.override_status is None:
                raise ValueError("override requires override_status")
        elif self.override_status is not None:
            raise ValueError("override_status is only valid with action=override")
        return self


class ErrorCategory(str, Enum):
    NONE = "none"
    VALIDATION = "validation"
    INGESTION = "ingestion"
    RETRIEVAL = "retrieval"
    GUARDRAIL = "guardrail"
    MODEL = "model"
    INTERNAL = "internal"


class RetrievalConfigRecord(_Strict):
    method: str  # e.g. "bm25", "vector", "hybrid_rrf"
    top_k: int = Field(ge=1)
    params: dict[str, float | int | str] = {}


class AuditRecord(_Strict):
    """Operational metadata only: identifiers and hashes, never raw text."""

    trace_id: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=utcnow)
    doc_ids: tuple[str, ...] = ()
    doc_sha256s: tuple[Sha256, ...] = ()
    query_sha256: Sha256 | None = None
    retrieval: RetrievalConfigRecord | None = None
    retrieved_chunk_ids: tuple[str, ...] = ()
    model_version: str | None = None
    prompt_version: str | None = None
    outcome: AssessmentStatus | None = None
    escalation_reason: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    error_category: ErrorCategory = ErrorCategory.NONE
    node_path: tuple[str, ...] = ()
    guardrail_flags: tuple[str, ...] = ()


class ClaimRequest(_Strict):
    """Untrusted user input. Validated before anything else happens."""

    query: str = Field(min_length=1, max_length=2000)
    doc_ids: tuple[str, ...] = Field(min_length=1, max_length=10)
    top_k: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if not self.query.strip():
            raise ValueError("query is blank")
        if len(set(self.doc_ids)) != len(self.doc_ids):
            raise ValueError("duplicate doc_ids")
        if any(not d.strip() for d in self.doc_ids):
            raise ValueError("blank doc_id")
        return self


class ResultKind(str, Enum):
    ASSESSED = "assessed"
    ABSTAINED = "abstained"
    REJECTED = "rejected"


class WorkflowResult(_Strict):
    trace_id: str
    kind: ResultKind
    assessment: Assessment | None = None
    reject_reason: str | None = None
    review_priority: str = "standard"  # "standard" | "mandatory"
    retrieved: tuple[EvidenceRef, ...] = ()
    quarantined_chunk_ids: tuple[str, ...] = ()
    notices: tuple[str, ...] = ()
    audit: AuditRecord

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if self.kind == ResultKind.REJECTED:
            if self.assessment is not None or not self.reject_reason:
                raise ValueError("rejected result: no assessment, a reason is required")
        elif self.assessment is None:
            raise ValueError("assessed/abstained result requires an assessment")
        return self