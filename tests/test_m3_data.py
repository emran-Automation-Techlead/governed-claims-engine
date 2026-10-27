import json
from pathlib import Path

import pytest

from claims_engine.chunking import chunk_document
from claims_engine.eval_common import load_jsonl
from claims_engine.eval_workflow import by_category, m2_system_view, summarize

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "eval"
STATUSES = {"potentially_covered", "potentially_excluded", "insufficient_evidence", "human_review_required"}
SETS = {"calibration_cases.jsonl": "CAL", "heldout_cases.jsonl": "HO", "adversarial_cases.jsonl": "ADV"}


def clauses(everything):
    return {(c.filename, c.clause_id) for d in everything.values() for c in chunk_document(d)}


@pytest.mark.parametrize("fname", sorted(SETS))
def test_case_files_are_well_formed(fname, everything):
    rows = load_jsonl(EV / fname)
    assert rows and all(r["id"].startswith(SETS[fname]) for r in rows)
    existing = clauses(everything)
    for r in rows:
        assert r["query"].strip() and r["lang"] in {"en", "fr", "de"} and r["scope"]
        assert all(s in everything for s in r["scope"]), r["id"]
        for ref in r["relevant"]:
            f, cl = ref.split("#")
            assert (f, cl) in existing, f"{r['id']}: {ref}"
            assert f in r["scope"] or fname == "adversarial_cases.jsonl"
        if fname != "calibration_cases.jsonl":
            assert r["primary"] in STATUSES and set(r["acceptable"]) <= STATUSES
            assert r["primary"] in r["acceptable"]


def test_calibration_set_only_touches_the_four_original_policies():
    originals = {"synthetic_home_policy.pdf", "synthetic_travel_policy.pdf",
                 "synthetic_home_policy_fr.pdf", "synthetic_home_policy_de.pdf"}
    for r in load_jsonl(EV / "calibration_cases.jsonl"):
        assert set(r["scope"]) <= originals


def test_heldout_and_adversarial_sets_exercise_the_required_scenarios():
    ho = {r["category"] for r in load_jsonl(EV / "heldout_cases.jsonl")}
    adv = {r["category"] for r in load_jsonl(EV / "adversarial_cases.jsonl")}
    assert {"clear", "paraphrase", "cross_lingual", "german_compound", "misleading_or_conflicting",
            "unanswerable"} <= ho
    assert {"query_injection", "injection_bypass", "cross_document", "poisoned_document"} <= adv
    langs = {(r["lang"], r["scope"][0]) for r in load_jsonl(EV / "heldout_cases.jsonl")}
    assert any(lang == "en" and ("_fr" in s or "_de" in s) for lang, s in langs)  # English about FR/DE text


def _norm(q: str) -> str:
    return " ".join(q.lower().split())


def test_query_sets_do_not_overlap_each_other_or_the_m2_set():
    sets = {
        "m2": {_norm(json.loads(x)["query"]) for x in (EV / "baseline_m2" / "retrieval_cases.jsonl")
               .read_text("utf-8").splitlines() if x.strip()},
        **{k: {_norm(r["query"]) for r in load_jsonl(EV / k)} for k in SETS}}
    names = list(sets)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert not (sets[a] & sets[b]), (a, b, sets[a] & sets[b])


def test_calibration_set_has_balanced_answerable_and_unanswerable_cases():
    rows = load_jsonl(EV / "calibration_cases.jsonl")
    ans = sum(bool(r["relevant"]) for r in rows)
    assert 30 <= ans <= 40 and len(rows) - ans >= 25
    assert {r["category"] for r in rows if not r["relevant"]} >= {"off_topic", "adjacent", "function_words", "odd_input"}


# ---- metrics arithmetic ----
def row(status, primary, acceptable, **kw):
    base = {"status": status, "primary": primary, "acceptable": acceptable, "citation_errors": [],
            "leaked": [], "query_text_in_audit": False, "ms": 1.0, "id": "x", "category": "c",
            "relevant": [], "cited": []}
    base.update(kw)
    return base


def test_summarize_hand_calculated():
    C, X, I, R = ("potentially_covered", "potentially_excluded", "insufficient_evidence", "human_review_required")
    rows = [
        row(C, C, [C]),          # correct verdict
        row(X, C, [C]),          # wrong-direction (and unsupported) verdict
        row(C, I, [I]),          # unsupported verdict where abstention was expected
        row(I, C, [C]),          # over-abstention
        row(R, R, [R, I]),       # correct escalation
        row(I, I, [I]),          # correct abstention
    ]
    s = summarize(rows)
    assert s["n"] == 6 and s["verdict_rate"] == pytest.approx(3 / 6)
    assert s["unsupported_verdict_rate"] == pytest.approx(2 / 6)
    assert s["wrong_direction"] == 1
    assert s["verdict_coverage_on_verdict_cases"] == pytest.approx(2 / 3)
    assert s["abstention_quality"] == pytest.approx(2 / 3)  # expected-abstain cases: C(wrong), R ok, I ok
    assert s["over_abstention"] == pytest.approx(1 / 3)
    assert s["status_accuracy"] == pytest.approx(3 / 6) and s["acceptable_rate"] == pytest.approx(3 / 6)


def test_summarize_flags_leaks_and_audit_text_exposure():
    s = summarize([row("insufficient_evidence", "insufficient_evidence", ["insufficient_evidence"],
                       leaked=["c1"], citation_errors=["page_mismatch:c"], query_text_in_audit=True)])
    assert (s["scope_leaks"], s["citation_error_cases"], s["query_text_in_audit"]) == (1, 1, 1)


def test_m2_system_view_separates_good_off_target_and_abstained():
    rows = [
        row("potentially_covered", None, None, relevant=["f#1"], cited=["f#1"], id="a"),
        row("potentially_covered", None, None, relevant=["f#1"], cited=["f#2"], id="b"),
        row("insufficient_evidence", None, None, relevant=["f#1"], id="c"),
        row("insufficient_evidence", None, None, relevant=[], id="u1"),
        row("potentially_excluded", None, None, relevant=[], cited=["f#9"], id="u2"),
    ]
    v = m2_system_view(rows)
    assert v["verdict_with_only_relevant_citations"] == 1 and v["ids_off_target"] == ["b"]
    assert v["abstained_or_escalated"] == 1
    assert v["unanswerable_given_verdict"] == 1 and v["unanswerable_abstained"] == 1


def test_by_category_groups_rows():
    rows = [row("insufficient_evidence", "insufficient_evidence", ["insufficient_evidence"], category=k)
            for k in ("a", "a", "b")]
    g = by_category(rows)
    assert g["a"]["n"] == 2 and g["b"]["n"] == 1