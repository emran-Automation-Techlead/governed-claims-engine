import json
from pathlib import Path

import pytest

from claims_engine.calibrate import evaluate, pick
from claims_engine.chunking import chunk_document
from claims_engine.eval_common import rule_of_three, sha256_file
from claims_engine.retrieval import ChunkIndex, RetrievalConfig
from claims_engine.support import POLICY_PATH, AbstainPolicy, lexical_coverage, score_hit
from helpers import FakeEmbedder

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def home(everything):
    chunks = chunk_document(everything["synthetic_home_policy.pdf"])
    return chunks, ChunkIndex(chunks)


def chunk(chunks, clause):
    return next(c for c in chunks if c.clause_id == clause)


def test_policy_fails_closed_when_calibration_file_is_missing(tmp_path):
    p = AbstainPolicy.load(tmp_path / "nope.json")
    assert p.version == "fail-closed" and p.tau_lex > 1.0 and p.tau_sem is None


def test_fail_closed_policy_supports_nothing(home):
    chunks, idx = home
    hit = idx.search("burst pipe escape of water", RetrievalConfig(method="bm25")).hits[0]
    assert score_hit("burst pipe escape of water", hit, idx, AbstainPolicy()).supported is False


def test_policy_loads_from_json(tmp_path):
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"version": "v", "tau_lex": 0.4, "tau_sem": 0.7, "note": "n"}), "utf-8")
    p = AbstainPolicy.load(f)
    assert (p.version, p.tau_lex, p.tau_sem) == ("v", 0.4, 0.7)
    f.write_text(json.dumps({"version": "v", "tau_lex": 0.4, "tau_sem": None}), "utf-8")
    assert AbstainPolicy.load(f).tau_sem is None


def test_shipped_policy_is_calibrated_sane_and_tied_to_its_case_file():
    d = json.loads(POLICY_PATH.read_text("utf-8"))
    assert d["version"].startswith("cal-") and 0.0 < d["tau_lex"] <= 1.0
    assert d["tau_sem"] is None or 0.0 < d["tau_sem"] < 1.0
    # the policy records which labelled calibration file produced it: editing the file invalidates it
    assert d["calibration_cases_sha256"] == sha256_file(ROOT / "eval" / "calibration_cases.jsonl")
    assert "rule-of-three" in d["note"]


def test_full_overlap_scores_one_no_overlap_scores_zero(home):
    chunks, idx = home
    c = chunk(chunks, "3.1")
    assert lexical_coverage("burst pipes sudden accidental escape water", c, idx) == pytest.approx(1.0)
    assert lexical_coverage("recipe chocolate cake", c, idx) == 0.0


def test_stopword_only_or_empty_query_scores_zero(home):
    chunks, idx = home
    c = chunk(chunks, "3.1")
    assert lexical_coverage("what is the thing in the", c, idx) == 0.0
    assert lexical_coverage("", c, idx) == 0.0
    assert lexical_coverage("???", c, idx) == 0.0


def test_unknown_terms_lower_coverage(home):
    chunks, idx = home
    c = chunk(chunks, "3.1")
    full = lexical_coverage("burst pipes", c, idx)
    padded = lexical_coverage("burst pipes zzzunknownterm", c, idx)
    assert full == pytest.approx(1.0) and 0.0 < padded < full


def test_rare_term_weighs_more_than_common_term(home):
    chunks, idx = home
    c = chunk(chunks, "3.1")  # contains both 'water' (appears in several clauses) and 'plumbing' (rarer)
    only_rare = lexical_coverage("plumbing xxxx", c, idx)
    only_common = lexical_coverage("damage xxxx", c, idx)
    assert idx.term_idf("plumbing") > idx.term_idf("damage")
    assert only_rare > only_common


def test_semantic_gate_uses_cosine_when_threshold_set(home):
    chunks, _ = home
    idx = ChunkIndex(chunks, embedder=FakeEmbedder())
    hit = idx.search("zzz qqq", RetrievalConfig(method="vector", top_k=1)).hits[0]
    assert hit.cosine is not None
    low = AbstainPolicy(version="t", tau_lex=1.01, tau_sem=0.0)
    high = AbstainPolicy(version="t", tau_lex=1.01, tau_sem=1.01)
    assert score_hit("zzz qqq", hit, idx, low).supported is True
    assert score_hit("zzz qqq", hit, idx, high).supported is False
    assert score_hit("zzz qqq", hit, idx, AbstainPolicy()).supported is False  # tau_sem None -> ignored


# ---- calibration arithmetic ----
ROWS = [
    {"id": "a1", "answerable": True, "hits": [{"lex": 0.9, "cos": None, "relevant": True}]},
    {"id": "a2", "answerable": True, "hits": [{"lex": 0.6, "cos": None, "relevant": True}]},
    {"id": "a3", "answerable": True, "hits": [{"lex": 0.55, "cos": None, "relevant": False}]},
    {"id": "u1", "answerable": False, "hits": [{"lex": 0.5, "cos": None, "relevant": False}]},
    {"id": "u2", "answerable": False, "hits": [{"lex": 0.1, "cos": None, "relevant": False}]},
]


def test_evaluate_counts_answers_wrong_answers_and_false_accepts():
    e = evaluate(ROWS, 0.55, None)
    assert e["answer_rate"] == pytest.approx(2 / 3)
    assert e["answered_wrong_only"] == 1  # a3 is accepted but cites the wrong clause
    assert e["false_accepts"] == 0 and e["n_unans"] == 2
    e2 = evaluate(ROWS, 0.4, None)
    assert e2["false_accepts"] == 1 and e2["false_accept_ids"] == ["u1"]


def test_pick_returns_zero_false_accept_value_and_one_step_margin():
    grid = [0.1, 0.3, 0.5, 0.7]
    zero, chosen = pick(grid, lambda t: evaluate(ROWS, t, None))
    assert zero == 0.7  # u1 scores 0.5, so 0.1/0.3/0.5 all falsely accept it; 0.7 is the first clean value
    assert chosen == 0.7  # margin cannot exceed the grid
    zero, chosen = pick([0.1, 0.51, 0.6, 0.9], lambda t: evaluate(ROWS, t, None))
    assert (zero, chosen) == (0.51, 0.6)


def test_pick_reports_none_when_nothing_separates():
    assert pick([0.1, 0.2], lambda t: evaluate(ROWS, t, None)) == (None, None)


def test_rule_of_three():
    assert rule_of_three(28) == pytest.approx(3 / 28)
    assert rule_of_three(0) == 1.0 and rule_of_three(2) == 1.0