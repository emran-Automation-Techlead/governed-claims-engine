import pytest
from pydantic import ValidationError

from claims_engine.schemas import (
    Assessment,
    AuditRecord,
    DocumentRecord,
    ErrorCategory,
    EvidenceRef,
    HumanReview,
    PageStatus,
    PageText,
    ReviewAction,
    ReviewStatus,
)
from claims_engine.schemas import (
    AssessmentStatus as S,
)

H = "a" * 64


def ev(**kw):
    base = dict(doc_id="doc-1", doc_sha256=H, page_number=3, chunk_id="c1",
                clause_id="3.1", quote="We cover sudden and accidental escape of water")
    base.update(kw)
    return EvidenceRef(**base)


def assess(status, **kw):
    base = dict(status=status, summary="s", model_version="offline-rules-0", prompt_version="p0")
    base.update(kw)
    return Assessment(**base)


def test_evidence_valid_and_frozen():
    e = ev()
    with pytest.raises(ValidationError):
        e.page_number = 9


@pytest.mark.parametrize("kw", [dict(page_number=0), dict(doc_sha256="xyz"), dict(quote=""),
                                dict(chunk_id=""), dict(quote="x" * 1001)])
def test_evidence_rejects_bad_values(kw):
    with pytest.raises(ValidationError):
        ev(**kw)


def test_evidence_forbids_extra_fields():
    with pytest.raises(ValidationError):
        ev(unexpected=1)


def test_covered_requires_supporting_evidence():
    with pytest.raises(ValidationError):
        assess(S.POTENTIALLY_COVERED)
    a = assess(S.POTENTIALLY_COVERED, supporting_clauses=(ev(),))
    assert a.review_status == ReviewStatus.PENDING
    assert "not a binding" in a.disclaimer


def test_excluded_requires_exclusion_evidence():
    with pytest.raises(ValidationError):
        assess(S.POTENTIALLY_EXCLUDED, supporting_clauses=(ev(),))
    assess(S.POTENTIALLY_EXCLUDED, exclusions_and_limitations=(ev(),))


def test_insufficient_requires_missing_information():
    with pytest.raises(ValidationError):
        assess(S.INSUFFICIENT_EVIDENCE)
    assess(S.INSUFFICIENT_EVIDENCE, missing_information=("date of loss",))


def test_human_review_required_requires_reason():
    with pytest.raises(ValidationError):
        assess(S.HUMAN_REVIEW_REQUIRED)
    assess(S.HUMAN_REVIEW_REQUIRED, escalation_reason="conflicting clauses 3.1 and 3.2")


def test_unknown_status_rejected():
    with pytest.raises(ValidationError):
        assess("approved_for_payment")


def test_override_requires_reason_and_status():
    with pytest.raises(ValidationError):
        HumanReview(trace_id="t", reviewer_id="r", action=ReviewAction.OVERRIDE,
                    override_status=S.POTENTIALLY_COVERED)
    with pytest.raises(ValidationError):
        HumanReview(trace_id="t", reviewer_id="r", action=ReviewAction.OVERRIDE,
                    override_status=S.POTENTIALLY_COVERED, reason="   ")
    with pytest.raises(ValidationError):
        HumanReview(trace_id="t", reviewer_id="r", action=ReviewAction.OVERRIDE, reason="why")
    ok = HumanReview(trace_id="t", reviewer_id="r", action=ReviewAction.OVERRIDE,
                     override_status=S.HUMAN_REVIEW_REQUIRED, reason="policy endorsement missing")
    assert ok.timestamp.tzinfo is not None


def test_approve_and_reject_need_no_reason_but_forbid_override_status():
    HumanReview(trace_id="t", reviewer_id="r", action=ReviewAction.APPROVE)
    HumanReview(trace_id="t", reviewer_id="r", action=ReviewAction.REJECT)
    with pytest.raises(ValidationError):
        HumanReview(trace_id="t", reviewer_id="r", action=ReviewAction.APPROVE,
                    override_status=S.POTENTIALLY_COVERED)


def test_audit_record_defaults_and_no_raw_text_fields():
    a = AuditRecord(trace_id="t1")
    assert a.error_category == ErrorCategory.NONE
    for banned in ("query", "document_text", "prompt", "claim_text"):
        assert banned not in AuditRecord.model_fields
    with pytest.raises(ValidationError):
        AuditRecord(trace_id="t1", query="free text is not allowed here")
    with pytest.raises(ValidationError):
        AuditRecord(trace_id="t1", doc_sha256s=("short",))
    with pytest.raises(ValidationError):
        AuditRecord(trace_id="t1", latency_ms=-1)


def test_document_record_page_consistency():
    pages = (PageText(page_number=1, text="x" * 30, char_count=30, status=PageStatus.OK),)
    base = dict(doc_id="d", filename="f.pdf", version="1", sha256=H, size_bytes=10, pages=pages)
    DocumentRecord(page_count=1, **base)
    with pytest.raises(ValidationError):
        DocumentRecord(page_count=2, **base)
    bad = (PageText(page_number=2, text="x", char_count=1, status=PageStatus.EMPTY),)
    with pytest.raises(ValidationError):
        DocumentRecord(**{**base, "pages": bad}, page_count=1)
