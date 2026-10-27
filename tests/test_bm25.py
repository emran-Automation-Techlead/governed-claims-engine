import math

import pytest

from claims_engine.bm25 import BM25Index, tokenize
from claims_engine.config import BM25Params
from claims_engine.ingestion import ingest_pdf_path

CORPUS = [
    "burst pipe water damage sudden accidental",
    "gradual leakage seepage corrosion not covered",
    "fire lightning explosion cover",
    "water water water flood river",
]


def test_tokenizer_keeps_clause_ids_and_lowercases():
    assert tokenize("Clause 3.1: Burst-Pipes, EUR 1,500!") == ["clause", "3.1", "burst-pipes", "eur", "1", "500"]


def test_ranking_prefers_relevant_document():
    idx = BM25Index(CORPUS)
    assert idx.search("burst pipe", 3)[0].index == 0
    assert idx.search("lightning")[0].index == 2


def test_term_frequency_saturates_but_still_helps():
    idx = BM25Index(CORPUS)
    assert idx.search("water", 4)[0].index == 3  # three occurrences beat one


def test_rare_terms_outweigh_common_terms():
    idx = BM25Index(CORPUS)
    assert idx._idf["lightning"] > idx._idf["water"]


def test_idf_matches_formula():
    idx = BM25Index(CORPUS)
    n, df = 4, 2  # 'water' appears in 2 docs
    assert idx._idf["water"] == pytest.approx(math.log((n - df + 0.5) / (df + 0.5) + 1))


def test_score_matches_hand_calculation():
    docs = ["a b", "a c c"]
    idx = BM25Index(docs, BM25Params(k1=1.5, b=0.75))
    avgdl = 2.5
    idf_b = math.log((2 - 1 + 0.5) / (1 + 0.5) + 1)
    expected = idf_b * 1 * 2.5 / (1 + 1.5 * (1 - 0.75 + 0.75 * 2 / avgdl))
    assert idx.score("b", 0) == pytest.approx(expected)
    assert idx.score("b", 1) == 0.0


def test_no_match_returns_empty():
    assert BM25Index(CORPUS).search("zebra") == []


def test_empty_query_and_empty_corpus():
    assert BM25Index(CORPUS).search("") == []
    assert BM25Index([]).search("anything") == []


def test_top_k_limits_and_validates():
    idx = BM25Index(CORPUS)
    assert len(idx.search("water", 1)) == 1
    with pytest.raises(ValueError):
        idx.search("water", 0)


def test_deterministic_tie_break_by_index():
    idx = BM25Index(["alpha", "alpha", "alpha"])
    assert [h.index for h in idx.search("alpha", 3)] == [0, 1, 2]


def test_scores_sorted_descending():
    s = [h.score for h in BM25Index(CORPUS).search("water pipe flood", 4)]
    assert s == sorted(s, reverse=True)


def test_length_normalisation_favours_shorter_doc():
    idx = BM25Index(["cover fire", "cover fire " + "filler " * 50])
    assert idx.search("fire")[0].index == 0


def test_retrieves_correct_page_from_real_synthetic_pdf(policies):
    doc = ingest_pdf_path(policies["home"])
    idx = BM25Index([p.text for p in doc.pages])
    top = idx.search("gradual leakage seepage pipes", 1)[0]
    assert doc.pages[top.index].page_number == 3
    top = idx.search("unoccupied for more than 60 consecutive days", 1)[0]
    assert doc.pages[top.index].page_number == 4
    top = idx.search("excess per claim EUR 250", 1)[0]
    assert doc.pages[top.index].page_number == 5
