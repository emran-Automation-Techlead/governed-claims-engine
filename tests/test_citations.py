import pytest

from claims_engine.chunking import chunk_document
from claims_engine.citations import DocInfo, check_ref, validate_citations
from claims_engine.schemas import Assessment
from claims_engine.schemas import AssessmentStatus as S
from helpers import registry_of


@pytest.fixture(scope="module")
def setup(everything):
    home = everything["synthetic_home_policy.pdf"]
    travel = everything["synthetic_travel_policy.pdf"]
    chunks = chunk_document(home)
    retrieved = {c.chunk_id: c for c in chunks if c.clause_id in {"3.1", "3.2", "4.3"}}
    reg = registry_of([home, travel])
    chunk = next(c for c in chunks if c.clause_id == "3.2")
    return {"home": home, "travel": travel, "retrieved": retrieved, "reg": reg, "chunk": chunk,
            "travel_chunk": chunk_document(travel)[0]}


def codes(ref, s, allowed=None):
    allowed = allowed or [s["home"].doc_id]
    return sorted({e.code for e in check_ref(ref, s["retrieved"], allowed, s["reg"])})


def test_exact_reference_is_valid(setup):
    assert codes(setup["chunk"].to_evidence(), setup) == []


def test_quote_may_be_a_substring_and_whitespace_insensitive(setup):
    ref = setup["chunk"].to_evidence().model_copy(update={"quote": "We do   not cover\ndamage caused by gradual"})
    assert codes(ref, setup) == []


@pytest.mark.parametrize("update,code", [
    ({"chunk_id": "doc-x:p9:9.9"}, "unknown_chunk"),
    ({"doc_id": "doc-other"}, "doc_id_mismatch"),
    ({"doc_sha256": "0" * 64}, "doc_hash_mismatch"),
    ({"doc_version": "99"}, "version_mismatch"),
    ({"doc_version": None}, "missing_version"),
    ({"page_number": 2}, "page_mismatch"),
    ({"clause_id": "9.9"}, "clause_mismatch"),
    ({"clause_id": None}, "clause_mismatch"),
    ({"quote": "We cover everything, always."}, "quote_mismatch"),
])
def test_each_kind_of_bad_reference_is_rejected(setup, update, code):
    ref = setup["chunk"].to_evidence().model_copy(update=update)
    assert code in codes(ref, setup)


def test_a_real_chunk_from_another_document_is_out_of_scope_and_unknown(setup):
    ref = setup["travel_chunk"].to_evidence()
    got = codes(ref, setup)
    assert "unknown_chunk" in got  # not retrieved in this request
    retrieved = dict(setup["retrieved"], **{setup["travel_chunk"].chunk_id: setup["travel_chunk"]})
    errs = {e.code for e in check_ref(ref, retrieved, [setup["home"].doc_id], setup["reg"])}
    assert "out_of_scope" in errs  # even if it had been retrieved, scope forbids it


def test_registry_mismatch_detected(setup):
    reg = dict(setup["reg"])
    d = setup["home"]
    reg[d.doc_id] = DocInfo(d.doc_id, d.filename, "tampered-version", d.sha256)
    errs = {e.code for e in check_ref(setup["chunk"].to_evidence(), setup["retrieved"], [d.doc_id], reg)}
    assert "registry_mismatch" in errs
    del reg[d.doc_id]
    errs = {e.code for e in check_ref(setup["chunk"].to_evidence(), setup["retrieved"], [d.doc_id], reg)}
    assert "unregistered_document" in errs


def test_assessment_level_validation_collects_all_errors(setup):
    good = setup["chunk"].to_evidence()
    bad = good.model_copy(update={"page_number": 1, "quote": "invented"})
    a = Assessment(status=S.POTENTIALLY_EXCLUDED, summary="s", model_version="m", prompt_version="p",
                   exclusions_and_limitations=(good, bad))
    errs = validate_citations(a, setup["retrieved"], [setup["home"].doc_id], setup["reg"])
    assert sorted(e.code for e in errs) == ["page_mismatch", "quote_mismatch"]
    ok = Assessment(status=S.POTENTIALLY_EXCLUDED, summary="s", model_version="m", prompt_version="p",
                    exclusions_and_limitations=(good,))
    assert validate_citations(ok, setup["retrieved"], [setup["home"].doc_id], setup["reg"]) == []


def test_verdict_without_citation_is_flagged_even_if_schema_is_bypassed(setup):
    a = Assessment.model_construct(status=S.POTENTIALLY_COVERED, summary="s", supporting_clauses=(),
                                   exclusions_and_limitations=())
    errs = validate_citations(a, setup["retrieved"], [setup["home"].doc_id], setup["reg"])
    assert [e.code for e in errs] == ["no_citation"]
    b = Assessment.model_construct(status=S.POTENTIALLY_EXCLUDED, summary="s", supporting_clauses=(),
                                   exclusions_and_limitations=())
    assert [e.code for e in validate_citations(b, setup["retrieved"], [setup["home"].doc_id],
                                               setup["reg"])] == ["no_citation"]


def test_abstentions_need_no_citations(setup):
    a = Assessment(status=S.INSUFFICIENT_EVIDENCE, summary="s", missing_information=("x",),
                   model_version="m", prompt_version="p")
    assert validate_citations(a, {}, [], {}) == []