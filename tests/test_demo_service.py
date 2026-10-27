import json
import threading

import pytest

from claims_engine import render
from claims_engine.demo_service import EXAMPLES, LIMITATIONS, REVIEWER_RE, DemoService
from claims_engine.schemas import ResultKind

HOME, TRAVEL = "synthetic_home_policy.pdf", "synthetic_travel_policy.pdf"
QUESTION = "burst pipes sudden accidental escape water"


@pytest.fixture(scope="module")
def svc():
    return DemoService.build()


@pytest.fixture(scope="module")
def ids(svc):
    return {d.filename: d.doc_id for d in svc.documents()}


# ---------------------------------------------------------------- documents and scope
def test_documents_expose_hash_version_and_flag_only_the_adversarial_one(svc):
    docs = svc.documents()
    assert len(docs) == 8 and len({d.doc_id for d in docs}) == 8
    assert all(len(d.sha256) == 64 and d.version and d.filename in d.label for d in docs)
    assert [d.filename for d in docs if d.adversarial] == ["synthetic_poisoned_policy.pdf"]


def test_adversarial_document_can_be_left_out():
    s = DemoService.build(include_adversarial=False)
    assert len(s.documents()) == 7 and not any(d.adversarial for d in s.documents())


def test_scope_text_names_exactly_the_selected_documents(svc, ids):
    text = render.scope_md(svc.scope_of([ids[HOME]]))
    assert HOME in text and TRAVEL not in text and "Only these will be searched or cited" in text
    assert "none selected" in render.scope_md([]).lower()


def test_assessment_uses_only_the_selected_document(svc, ids):
    run = svc.assess(QUESTION, [ids[HOME]])
    r = run.result
    assert {d.filename for d in run.scope} == {HOME}
    assert r.audit.doc_ids == (ids[HOME],)
    assert r.retrieved and all(e.doc_id == ids[HOME] for e in r.retrieved)
    assert all(e.doc_id == ids[HOME] for e in
               (*r.assessment.supporting_clauses, *r.assessment.exclusions_and_limitations))


def test_another_policys_topic_is_invisible_when_not_selected(svc, ids):
    run = svc.assess("baggage limit single item lost stolen", [ids[HOME]])
    assert svc.kind_label(run.result) == "insufficient"
    assert all(e.doc_id == ids[HOME] for e in run.result.retrieved)
    run2 = svc.assess("baggage limit single item lost stolen", [ids[TRAVEL]])
    assert svc.kind_label(run2.result) == "supported"
    assert {e.doc_id for e in run2.result.retrieved} == {ids[TRAVEL]}


# ---------------------------------------------------------------- the curated examples are real behaviour
@pytest.mark.parametrize("label,files,question,expected", EXAMPLES, ids=[e[0][:30] for e in EXAMPLES])
def test_every_curated_example_behaves_as_labelled(svc, ids, label, files, question, expected):
    run = svc.assess(question, [ids[f] for f in files])
    assert svc.kind_label(run.result) == expected, label


# ---------------------------------------------------------------- request isolation
def test_consecutive_requests_never_reuse_evidence_state_or_trace(svc, ids):
    a = svc.assess(QUESTION, [ids[HOME]]).result
    b = svc.assess("baggage limit single item lost stolen", [ids[TRAVEL]]).result
    assert a.trace_id != b.trace_id
    assert {e.chunk_id for e in a.retrieved}.isdisjoint({e.chunk_id for e in b.retrieved})
    assert {e.doc_id for e in b.retrieved} == {ids[TRAVEL]}
    assert svc.get(a.trace_id).result is a and svc.get(b.trace_id).result is b


def test_concurrent_requests_do_not_bleed_into_each_other(svc, ids):
    jobs = [(QUESTION, HOME), ("baggage limit single item lost stolen", TRAVEL),
            ("war invasion terrorist acts", HOME), ("hazardous activities skydiving professional sports", TRAVEL),
            ("racing rallies speed trials track days", "synthetic_motor_policy.pdf")] * 4
    out: list = [None] * len(jobs)

    def work(i, q, f):
        out[i] = (f, svc.assess(q, [ids[f]]))

    threads = [threading.Thread(target=work, args=(i, q, f)) for i, (q, f) in enumerate(jobs)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len({r.result.trace_id for _, r in out}) == len(jobs)
    for f, r in out:
        assert {e.doc_id for e in r.result.retrieved} <= {ids[f]}
        assert r.result.audit.doc_ids == (ids[f],)
    same = [(q, f) for q, f in jobs]
    solo = {(q, f): svc.assess(q, [ids[f]]).result.assessment for q, f in set(same)}
    for (q, f), (_, r) in zip(jobs, out, strict=True):
        assert r.result.assessment == solo[(q, f)]  # concurrency does not change the answer


def test_review_of_one_trace_does_not_touch_another(svc, ids):
    a = svc.assess(QUESTION, [ids[HOME]]).result.trace_id
    b = svc.assess(QUESTION, [ids[HOME]]).result.trace_id
    entry, err = svc.review(a, "reviewer-1", "approve", None, None)
    assert err is None and entry
    assert len(svc.get(a).reviews) == 1 and svc.get(b).reviews == []


# ---------------------------------------------------------------- invalid inputs never raise
@pytest.mark.parametrize("query,doc_ids", [
    (None, None), ("", ["x"]), ("   ", None), (QUESTION, []), (QUESTION, None), (QUESTION, "not-a-list"),
    (QUESTION, ["doc-unknown"]), ("a" * 2001, None), (12345, None), (QUESTION, [None]),
])
def test_invalid_input_is_rejected_cleanly_and_audited(svc, ids, query, doc_ids):
    if doc_ids is None and query == "a" * 2001:
        doc_ids = [ids[HOME]]
    if doc_ids is None and query == QUESTION:
        doc_ids = None
    run = svc.assess(query, doc_ids)
    assert run.result.kind == ResultKind.REJECTED and run.result.reject_reason
    assert svc.kind_label(run.result) == "rejected"
    assert svc.audit(run.result.trace_id)["result_kind"] == "rejected"
    html = render.status_html(run, svc.mode)
    assert "REQUEST REJECTED" in html and "ce-bad" in html


def test_rejection_reason_does_not_echo_the_question(svc):
    secret = "SECRET-NAME-98765"
    run = svc.assess(secret, ["doc-unknown"])
    assert secret not in run.result.reject_reason and secret not in repr(svc.audit(run.result.trace_id))


# ---------------------------------------------------------------- reviewer workflow
def fresh(svc, ids, question=QUESTION, doc=HOME):
    return svc.assess(question, [ids[doc]]).result.trace_id


def test_approve_is_recorded_and_original_assessment_is_unchanged(svc, ids):
    tid = fresh(svc, ids)
    before = svc.get(tid).result.assessment
    entry, err = svc.review(tid, "reviewer-1", "approve", None, "looks right")
    assert err is None and entry.action == "approve" and entry.effective_status == "potentially_covered"
    run = svc.get(tid)
    assert run.result.assessment == before and run.result.assessment.review_status.value == "pending"
    assert run.reviews == [entry]


def test_override_requires_status_and_a_real_explanation(svc, ids):
    tid = fresh(svc, ids)
    for status, reason in [("human_review_required", None), ("human_review_required", ""),
                           ("human_review_required", "short"), ("human_review_required", "          "),
                           (None, "a perfectly good explanation"), ("nonsense", "a perfectly good explanation")]:
        entry, err = svc.review(tid, "reviewer-1", "override", status, reason)
        assert entry is None and err, (status, reason)
    assert svc.get(tid).reviews == []


def test_valid_override_keeps_both_the_proposal_and_the_outcome(svc, ids):
    tid = fresh(svc, ids)
    entry, err = svc.review(tid, "reviewer-2", "override", "potentially_excluded",
                            "Clause 4.3 (unoccupied > 60 days) may apply.")
    assert err is None
    assert (entry.proposed_status, entry.effective_status, entry.override_status) == (
        "potentially_covered", "potentially_excluded", "potentially_excluded")
    hist = svc.audit(tid)["review_history"]
    assert hist[0]["proposed_status"] == "potentially_covered" and hist[0]["reason"].startswith("Clause 4.3")
    assert svc.audit(tid)["assessment_status"] == "potentially_covered"  # audit keeps the ORIGINAL outcome
    assert any(e["event"] == "human_review" and e["trace_id"] == tid for e in svc.sink.events)


@pytest.mark.parametrize("bad", ["", "   ", "a@b.com", "<script>x</script>", "x" * 65, "name/slash", "tab\there"])
def test_reviewer_id_must_be_a_pseudonym(svc, ids, bad):
    entry, err = svc.review(fresh(svc, ids), bad, "approve", None, None)
    assert entry is None and "Reviewer id" in err
    assert not REVIEWER_RE.match(bad.strip())  # the service strips first, then validates


@pytest.mark.parametrize("action", ["reject", "delete", "", None, "APPROVE "])
def test_only_approve_and_override_are_offered(svc, ids, action):
    entry, err = svc.review(fresh(svc, ids), "reviewer-1", action, None, None)
    assert entry is None and err


def test_review_without_or_with_unknown_trace_or_for_rejected_request(svc):
    assert svc.review(None, "reviewer-1", "approve", None, None)[1].startswith("No assessment")
    assert svc.review("not-a-trace", "reviewer-1", "approve", None, None)[1].startswith("No assessment")
    rej = svc.assess("", ["x"]).result.trace_id
    assert "rejected" in svc.review(rej, "reviewer-1", "approve", None, None)[1]


def test_overlong_explanation_is_refused(svc, ids):
    entry, err = svc.review(fresh(svc, ids), "reviewer-1", "override", "human_review_required", "x" * 1001)
    assert entry is None and "too long" in err


def test_review_can_be_recorded_for_escalations_and_abstentions_too(svc, ids):
    esc = svc.assess("exclusion 3.1 does not apply licence expired 30 days", [ids["synthetic_motor_policy.pdf"]])
    abst = svc.assess("earthquake damage to my house", [ids[HOME]])
    for run in (esc, abst):
        entry, err = svc.review(run.result.trace_id, "reviewer-1", "approve", None, None)
        assert err is None and entry.effective_status == run.result.assessment.status.value


# ---------------------------------------------------------------- audit
def test_audit_record_has_trace_hash_version_evidence_status_and_history(svc, ids):
    tid = fresh(svc, ids)
    svc.review(tid, "reviewer-1", "approve", None, None)
    a = svc.audit(tid)
    doc = svc.doc(ids[HOME])
    assert a["trace_id"] == tid and a["assessment_status"] == "potentially_covered"
    assert a["documents"] == [{"doc_id": doc.doc_id, "filename": HOME, "version": doc.version, "sha256": doc.sha256}]
    assert a["retrieved_chunk_ids"] and all(c.startswith(doc.doc_id) for c in a["retrieved_chunk_ids"])
    assert a["node_path"][0] == "validate_input" and a["node_path"][-1] == "audit"
    assert len(a["question_sha256"]) == 64 and a["question_text_stored"] is False
    assert len(a["review_history"]) == 1 and a["retrieval"]["params"]["abstain_policy"].startswith("cal-")
    assert svc.audit("nope") is None and svc.audit(None) is None


def test_question_text_is_stored_nowhere(svc, ids):
    secret = "my-very-private-claim-story burst pipes sudden accidental escape water"
    run = svc.assess(secret, [ids[HOME]])
    tid = run.result.trace_id
    svc.review(tid, "reviewer-1", "approve", None, "fine")
    blob = json.dumps(svc.audit(tid)) + repr(run.result) + json.dumps(svc.sink.events, default=str)
    assert "private-claim-story" not in blob


def test_flagged_cases_record_flags_and_quarantine_in_the_audit(svc, ids):
    run = svc.assess("storm damage to my roof", [ids["synthetic_poisoned_policy.pdf"]])
    a = svc.audit(run.result.trace_id)
    assert a["quarantined_chunk_ids"] and any(f.startswith("evidence:") for f in a["guardrail_flags"])
    assert a["review_priority"] == "mandatory"


def test_run_store_is_bounded_and_recent_is_newest_first(ids):
    s = DemoService.build(include_adversarial=False)
    d = s.documents()[0].doc_id
    tids = [s.assess(QUESTION, [d]).result.trace_id for _ in range(5)]
    s2 = DemoService(s.workflow, s.documents(), max_stored=3)
    tids2 = [s2.assess(QUESTION, [d]).result.trace_id for _ in range(5)]
    assert s2.get(tids2[0]) is None and s2.get(tids2[-1]) is not None
    assert [t for _, t in s2.recent()] == tids2[-3:][::-1] and tids


def test_jsonl_audit_log_can_be_enabled(tmp_path):
    s = DemoService.build(include_adversarial=False, audit_log=tmp_path / "audit.jsonl")
    d = s.documents()[0].doc_id
    r = s.assess("my private story burst pipes", [d])
    s.review(r.result.trace_id, "reviewer-1", "approve", None, None)
    lines = (tmp_path / "audit.jsonl").read_text("utf-8").splitlines()
    assert [json.loads(x)["event"] for x in lines] == ["assessment", "human_review"]
    assert "private story" not in "".join(lines)


# ---------------------------------------------------------------- limitations and rendering
def test_limitations_cover_every_required_point():
    text = " ".join(LIMITATIONS).lower()
    for needle in ("synthetic", "deterministic", "same author", "authentication is not implemented",
                   "not production-ready", "not legally certified", "not a legally binding"):
        assert needle in text, needle
    banner = render.limitations_html(compact=True).lower()
    for needle in ("synthetic", "deterministic", "self-authored", "no authentication", "not production-ready",
                   "legally certified"):
        assert needle in banner


def test_supported_review_insufficient_and_rejected_are_visually_and_verbally_distinct(svc, ids):
    sup = render.status_html(svc.assess(QUESTION, [ids[HOME]]), svc.mode)
    rev = render.status_html(svc.assess("excess EUR 250 each claim", [ids[HOME]]), svc.mode)
    ins = render.status_html(svc.assess("earthquake damage", [ids[HOME]]), svc.mode)
    rej = render.status_html(svc.assess("", None), svc.mode)
    assert "SUPPORTED PRELIMINARY ASSESSMENT" in sup and "ce-ok" in sup and "HUMAN REVIEW" not in sup
    assert "HUMAN REVIEW REQUIRED" in rev and "ce-warn" in rev and "SUPPORTED" not in rev
    assert "INSUFFICIENT EVIDENCE" in ins and "ce-neutral" in ins and "SUPPORTED" not in ins
    assert "REQUEST REJECTED" in rej and "ce-bad" in rej
    assert "mandatory" in rev.lower() and "standard" in sup.lower()


def test_evidence_shows_exact_page_clause_document_and_excerpt(svc, ids):
    html = render.evidence_html(svc.assess(QUESTION, [ids[HOME]]))
    assert "Clause 3.1 - page 3" in html and HOME in html and "v1" in html
    assert "3.1 Burst Pipes. We cover sudden and accidental escape of water" in html
    assert "Other passages considered but not cited" in html and "supports cover" in html


def test_page_spanning_clause_shows_both_pages(svc, ids):
    html = render.evidence_html(svc.assess("used for hire or reward taxi delivery work",
                                           [ids["synthetic_motor_policy.pdf"]]))
    assert "Clause 3.3 - page 3" in html and "Clause 3.3 - page 4" in html and "Business Use Extension" in html


def test_escalation_reasons_uncertainty_and_missing_information_are_shown(svc, ids):
    esc = svc.assess("exclusion 3.1 does not apply licence expired 30 days", [ids["synthetic_motor_policy.pdf"]])
    html = render.reasons_html(esc)
    assert "Reason for escalation" in html and "exception" in html.lower()
    cond = render.reasons_html(svc.assess("used for hire or reward taxi delivery work",
                                          [ids["synthetic_motor_policy.pdf"]]))
    assert "Missing information" in cond and "Business Use Extension" in cond and "Uncertainty" in cond


def test_quarantined_policy_text_is_never_rendered(svc, ids):
    run = svc.assess("storm damage to my roof", [ids["synthetic_poisoned_policy.pdf"]])
    page = render.status_html(run, svc.mode) + render.reasons_html(run) + render.evidence_html(run)
    assert "ignore all previous instructions" not in page.lower()
    assert "passage(s) were quarantined by the injection tripwire and are NOT shown or used" in page
    assert "instruction-like" in page


def test_untrusted_text_is_html_escaped_everywhere(svc, ids):
    from claims_engine.demo_service import ReviewEntry
    from claims_engine.schemas import utcnow

    run = svc.assess(QUESTION, [ids[HOME]])
    evil = "<script>alert(1)</script><img src=x onerror=alert(2)>"
    ev = run.result.assessment.supporting_clauses[0].model_copy(update={"quote": evil})
    assert "<script>" not in render._card(ev, svc.doc(ids[HOME]), "x", "t")
    run.reviews.append(ReviewEntry(evil[:20], "approve", "potentially_covered", "potentially_covered", None,
                                   evil, utcnow()))
    html = render.reviews_html(run)
    assert "<script>" not in html and "&lt;script&gt;" in html
    audit = render.audit_summary_html({**svc.audit(run.result.trace_id), "escalation_reason": evil})
    assert "<script>" not in audit
    rej = svc.assess(evil, ["<img src=x onerror=alert(3)>"])
    assert "<img" not in render.status_html(rej, svc.mode)


def test_audit_html_shows_hash_version_ids_and_privacy_note(svc, ids):
    tid = fresh(svc, ids)
    html = render.audit_summary_html(svc.audit(tid))
    doc = svc.doc(ids[HOME])
    assert doc.sha256 in html and f"v{doc.version}" in html and tid in html and "not stored" in html