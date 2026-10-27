import json

import pytest

from claims_engine.review import (
    JsonlAuditSink,
    MemoryAuditSink,
    ReviewError,
    apply_review,
)
from claims_engine.schemas import AssessmentStatus as S
from claims_engine.schemas import HumanReview, ReviewAction, ReviewStatus
from helpers import ask, make_wf


@pytest.fixture(scope="module")
def result(everything):
    wf, ids = make_wf(everything)
    return ask(wf, ids, "synthetic_home_policy.pdf", "burst pipes sudden accidental escape water")


def review(result, **kw):
    base = {"trace_id": result.trace_id, "reviewer_id": "reviewer-1", "action": ReviewAction.APPROVE}
    base.update(kw)
    return HumanReview(**base)


def test_approve_keeps_the_proposed_status(result):
    out = apply_review(result, review(result))
    assert out.review_status == ReviewStatus.APPROVED and out.effective_status == S.POTENTIALLY_COVERED
    assert out.proposed is result.assessment and result.assessment.review_status == ReviewStatus.PENDING


def test_reject_has_no_effective_status(result):
    out = apply_review(result, review(result, action=ReviewAction.REJECT, reason="not convinced"))
    assert out.review_status == ReviewStatus.REJECTED and out.effective_status is None


def test_override_needs_reason_and_status_and_records_both(result):
    with pytest.raises(ValueError):
        review(result, action=ReviewAction.OVERRIDE, override_status=S.POTENTIALLY_EXCLUDED)
    with pytest.raises(ValueError):
        review(result, action=ReviewAction.OVERRIDE, reason="clause 4.3 applies")
    out = apply_review(result, review(result, action=ReviewAction.OVERRIDE,
                                      override_status=S.HUMAN_REVIEW_REQUIRED, reason="clause 4.3 applies"))
    assert out.review_status == ReviewStatus.OVERRIDDEN and out.effective_status == S.HUMAN_REVIEW_REQUIRED
    assert out.proposed.status == S.POTENTIALLY_COVERED  # the original proposal is preserved for audit


def test_review_of_the_wrong_trace_is_refused(result):
    with pytest.raises(ReviewError, match="trace_id"):
        apply_review(result, review(result, trace_id="someone-elses-trace"))


def test_rejected_requests_cannot_be_reviewed(everything):
    wf, _ = make_wf(everything)
    r = wf.run({"nope": 1})
    with pytest.raises(ReviewError, match="no assessment"):
        apply_review(r, HumanReview(trace_id=r.trace_id, reviewer_id="x", action=ReviewAction.APPROVE))


def test_reviewer_actions_are_written_to_the_audit_trail(result):
    sink = MemoryAuditSink()
    apply_review(result, review(result, action=ReviewAction.OVERRIDE, override_status=S.POTENTIALLY_EXCLUDED,
                                reason="see 4.3"), sink)
    (e,) = sink.events
    assert e["event"] == "human_review" and e["trace_id"] == result.trace_id
    assert (e["reviewer_id"], e["action"], e["override_status"], e["reason"]) == (
        "reviewer-1", "override", "potentially_excluded", "see 4.3")
    assert e["proposed_status"] == "potentially_covered" and e["timestamp"]


def test_jsonl_sink_appends_valid_json_lines(tmp_path, result):
    sink = JsonlAuditSink(tmp_path / "logs" / "audit.jsonl")
    apply_review(result, review(result), sink)
    apply_review(result, review(result, action=ReviewAction.REJECT), sink)
    lines = (tmp_path / "logs" / "audit.jsonl").read_text("utf-8").splitlines()
    assert [json.loads(x)["action"] for x in lines] == ["approve", "reject"]


def test_workflow_audit_events_can_be_persisted_without_raw_text(everything, tmp_path):
    sink = JsonlAuditSink(tmp_path / "a.jsonl")
    wf, ids = make_wf(everything, sink=sink)
    ask(wf, ids, "synthetic_home_policy.pdf", "my private story about burst pipes sudden accidental escape water")
    text = (tmp_path / "a.jsonl").read_text("utf-8")
    assert "private story" not in text and json.loads(text)["node_path"][0] == "validate_input"