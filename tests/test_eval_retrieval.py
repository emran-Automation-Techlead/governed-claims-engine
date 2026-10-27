import json
from pathlib import Path

import pytest

from claims_engine.eval_retrieval import (
    KS,
    build_corpus,
    clause_keys,
    load_cases,
    render_report,
    run_arm,
    score_case,
    summarize,
)
from claims_engine.retrieval import ChunkIndex

CASES = Path(__file__).resolve().parents[1] / "eval" / "retrieval_cases.jsonl"
CATEGORIES = {"exact_id", "lexical", "paraphrase", "multilingual", "cross_lingual", "unanswerable"}


@pytest.fixture(scope="module")
def corpus(all_policies):
    chunks, ids = build_corpus(next(iter(all_policies.values())).parent)
    return chunks, ids


def test_dataset_is_well_formed():
    cases = load_cases(CASES)
    assert len(cases) >= 50
    for c in cases:
        assert set(c) == {"id", "category", "lang", "scope", "query", "relevant"}
        assert c["category"] in CATEGORIES and c["lang"] in {"en", "fr", "de"}
        assert c["query"].strip() and len(c["scope"]) == 1
        assert (c["category"] == "unanswerable") == (c["relevant"] == [])


def test_every_label_points_at_a_real_clause(corpus):
    chunks, _ = corpus
    existing = {(c.filename, c.clause_id) for c in chunks}
    for c in load_cases(CASES):
        for clause in c["relevant"]:
            assert (c["scope"][0], clause) in existing, f"{c['id']}: {clause} not in {c['scope']}"


def test_dataset_covers_each_language_and_category():
    cases = load_cases(CASES)
    assert {c["category"] for c in cases} == CATEGORIES
    assert {c["lang"] for c in cases} == {"en", "fr", "de"}


def test_duplicate_case_ids_rejected(tmp_path):
    p = tmp_path / "c.jsonl"
    row = json.dumps({"id": "Q1"})
    p.write_text(row + "\n" + row + "\n", "utf-8")
    with pytest.raises(ValueError):
        load_cases(p)


def test_metrics_hand_calculated():
    ranked = [("d", "9.9"), ("d", "1.2"), ("d", "3.4"), ("d", "5.6")]
    s = score_case(ranked, "d", ["1.2", "5.6"])
    assert s["first_rank"] == 2 and s["rr"] == 0.5
    assert (s["recall@1"], s["recall@3"], s["recall@5"]) == (0.0, 0.5, 1.0)
    assert (s["hit@1"], s["hit@3"]) == (0.0, 1.0)
    miss = score_case(ranked, "d", ["7.7"])
    assert miss["first_rank"] is None and miss["rr"] == 0.0 and miss["recall@5"] == 0.0
    other_doc = score_case(ranked, "other", ["1.2"])  # same clause id, wrong document
    assert other_doc["hit@5"] == 0.0


def test_summarize_averages_and_handles_empty():
    a = score_case([("d", "1")], "d", ["1"])
    b = score_case([("d", "2")], "d", ["1"])
    s = summarize([a, b])
    assert s["n"] == 2 and s["MRR"] == 0.5 and s["recall@1"] == 0.5
    assert summarize([]) == {"n": 0}
    assert KS == (1, 3, 5)


def test_clause_keys_collapse_split_clauses(corpus):
    chunks, _ = corpus
    dup = [chunks[0], chunks[0].model_copy(update={"chunk_id": "x"}), chunks[1]]
    assert clause_keys(dup) == [(chunks[0].filename, chunks[0].clause_id),
                                (chunks[1].filename, chunks[1].clause_id)]


def test_lexical_benchmark_end_to_end_is_deterministic_and_sane(corpus):
    chunks, ids = corpus
    cases = load_cases(CASES)
    idx = ChunkIndex(chunks)
    a = run_arm("bm25", idx, "bm25", cases, ids)
    b = run_arm("bm25", idx, "bm25", cases, ids)
    strip = lambda arm: [(r["id"], r["top"]) for r in arm["per_case"]]
    assert strip(a) == strip(b)
    assert a["overall"]["n"] == sum(1 for c in cases if c["relevant"])
    # exact clause identifiers must be solved by the lexical ranker (a property, not a score claim)
    assert a["by_category"]["exact_id"]["recall@1"] == 1.0
    assert 0.0 <= a["overall"]["MRR"] <= 1.0


def test_report_renders_only_measured_arms(corpus):
    chunks, ids = corpus
    arm = run_arm("bm25 only", ChunkIndex(chunks), "bm25", load_cases(CASES), ids)
    text = render_report({
        "date": "2000-01-01", "n_docs": len(ids), "n_chunks": len(chunks), "corpus_fp": "x",
        "n_cases": 52, "n_answerable": 49, "embedding": None, "deterministic": True,
        "arms": [arm], "limitations": ["l1"]})
    assert "NOT RUN" in text and "bm25 only" in text and "vector" not in text.split("## Overall")[1]

def test_main_runs_end_to_end_lexical_only_and_writes_report(tmp_path, monkeypatch, capsys):
    import sys

    from claims_engine import eval_retrieval

    policies = Path(__file__).resolve().parents[1] / "data" / "policies"
    monkeypatch.setattr(sys, "argv", ["x", "--no-semantic", "--policies", str(policies),
                                      "--out", str(tmp_path)])
    eval_retrieval.main()
    report = (tmp_path / "RETRIEVAL_REPORT.md").read_text("utf-8")
    data = json.loads((tmp_path / "results" / "retrieval_results.json").read_text("utf-8"))
    assert "NOT RUN" in report and "Limitations" in report
    assert [a["arm"] for a in data["arms"]] == ["bm25 (M1 ascii tokenizer)", "bm25 (multilingual)"]
    assert data["deterministic"] is True and data["embedding"] is None