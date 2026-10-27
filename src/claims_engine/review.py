"""Human review and audit sinks.

* `apply_review` never mutates the assessment: it returns a `ReviewedAssessment` carrying the
  original proposal, the reviewer's action and the effective status. An override requires a
  reason and an explicit status (enforced by the HumanReview schema).
* Sinks store `AuditRecord`s / review events as JSON lines. They hold identifiers and hashes,
  never claim or policy text.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .schemas import (
    Assessment,
    AssessmentStatus,
    AuditRecord,
    HumanReview,
    ReviewAction,
    ReviewStatus,
    WorkflowResult,
)

_STATUS = {ReviewAction.APPROVE: ReviewStatus.APPROVED, ReviewAction.REJECT: ReviewStatus.REJECTED,
           ReviewAction.OVERRIDE: ReviewStatus.OVERRIDDEN}


class ReviewError(ValueError):
    pass


@dataclass(frozen=True)
class ReviewedAssessment:
    proposed: Assessment
    review: HumanReview
    review_status: ReviewStatus
    effective_status: AssessmentStatus | None  # None when the reviewer rejected the proposal


class AuditSink(Protocol):
    def write(self, event: dict) -> None: ...


@dataclass
class MemoryAuditSink:
    events: list[dict] = field(default_factory=list)

    def write(self, event: dict) -> None:
        self.events.append(event)


@dataclass
class JsonlAuditSink:
    path: Path

    def write(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def audit_event(record: AuditRecord) -> dict:
    return {"event": "assessment", **json.loads(record.model_dump_json())}


def apply_review(result: WorkflowResult, review: HumanReview,
                 sink: AuditSink | None = None) -> ReviewedAssessment:
    if result.assessment is None:
        raise ReviewError("a rejected request has no assessment to review")
    if review.trace_id != result.trace_id:
        raise ReviewError("review.trace_id does not match the assessment's trace_id")
    a = result.assessment
    if a.review_status != ReviewStatus.PENDING:
        raise ReviewError("assessment already reviewed")
    if review.action == ReviewAction.APPROVE:
        effective: AssessmentStatus | None = a.status
    elif review.action == ReviewAction.OVERRIDE:
        effective = review.override_status
    else:
        effective = None
    out = ReviewedAssessment(a, review, _STATUS[review.action], effective)
    if sink is not None:
        sink.write({"event": "human_review", "trace_id": review.trace_id,
                    "reviewer_id": review.reviewer_id, "action": review.action.value,
                    "override_status": review.override_status.value if review.override_status else None,
                    "reason": review.reason, "proposed_status": a.status.value,
                    "timestamp": review.timestamp.isoformat()})
    return out