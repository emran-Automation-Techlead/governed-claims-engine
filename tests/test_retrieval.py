import math
import re

import numpy as np
import pytest

from claims_engine.chunking import chunk_document
from claims_engine.ingestion import ingest_pdf_path
from claims_engine.retrieval import (
    METHODS,
    ChunkIndex,
    RetrievalConfig,
    SemanticRetrievalDisabled,
    corpus_fingerprint,
    rrf_fuse,
)
from claims_engine.schemas import AuditRecord


class FakeEmbedder:
    """Deterministic letter-frequency 'embedding' so the vector/hybrid code paths run offline."""

    model_id, revision = "fake", "fake-rev"

    def encode(self, texts):
        out = []
        for t in texts:
            v = np.zeros(26, dtype=np.float32)
            for ch in re.sub(r"[^a-z]", "", t.lower()):
                v[ord(ch) - 97] += 1
            n = np.linalg.norm(v)
            out.append(list(map(float, v / n if n else v)))
        return out


@pytest.fixture(scope="module")
def corpus(all_policies):
    chunks, ids = [], {}
    for name, path in sorted(all_policies.items()):
        doc = ingest_pdf_path(path)
        ids[name] = doc.doc_id
        chunks += chunk_document(doc)
    return chunks, ids


# ---------- RRF ----------
def test_rrf_matches_hand_calculation():
    fused = dict(rrf_fuse([[10, 20, 30], [20, 30, 40]], k=60))
    assert fused[10] == pytest.approx(1 / 61)
    assert fused[20] == pytest.approx(1 / 62 + 1 / 61)
    assert fused[30] == pytest.approx(1 / 63 + 1 / 62)
    assert fused[40] == pytest.approx(1 / 63)


def test_rrf_orders_by_combined_score_and_rewards_agreement():
    fused = rrf_fuse([[1, 2, 3], [3, 2, 9]], k=60)
    order = [i for i, _ in fused]
    # 3: 1/63+1/61 = 0.032266 ; 2: 2/62 = 0.032258 -> a top rank edges out two mid ranks (convexity)
    assert order[:2] == [3, 2]
    assert dict(fused)[3] > dict(fused)[2] > dict(fused)[1] > dict(fused)[9]
    # an item both rankers like beats items only one ranker likes
    assert [i for i, _ in rrf_fuse([[1, 7], [2, 7]])][0] == 7


def test_rrf_single_list_preserves_order_and_top_k_truncates():
    assert [i for i, _ in rrf_fuse([[5, 4, 3, 2]])] == [5, 4, 3, 2]
    assert len(rrf_fuse([[5, 4, 3, 2]], top_k=2)) == 2


def test_rrf_ties_are_deterministic():
    # 1 and 2 each appear once at rank 1 in different lists: equal score, equal best rank -> id
    assert [i for i, _ in rrf_fuse([[2], [1]])] == [1, 2]
    assert rrf_fuse([[7, 8], [8, 7]]) == rrf_fuse([[7, 8], [8, 7]])


def test_rrf_k_changes_weighting_and_validates():
    small_k = dict(rrf_fuse([[1, 2]], k=1))
    big_k = dict(rrf_fuse([[1, 2]], k=1000))
    assert small_k[1] / small_k[2] > big_k[1] / big_k[2]
    with pytest.raises(ValueError):
        rrf_fuse([[1]], k=0)


def test_rrf_empty_inputs():
    assert rrf_fuse([]) == [] and rrf_fuse([[], []]) == []


# ---------- config ----------
def test_config_validation_and_fingerprint():
    with pytest.raises(ValueError):
        RetrievalConfig(method="magic")
    with pytest.raises(ValueError):
        RetrievalConfig(top_k=0)
    a, b = RetrievalConfig(), RetrievalConfig()
    assert a.fingerprint() == b.fingerprint()
    assert a.fingerprint() != RetrievalConfig(rrf_k=10).fingerprint()
    assert set(METHODS) == {"bm25", "vector", "hybrid_rrf"}


# ---------- lexical-only mode (no model) ----------
def test_lexical_only_bm25_finds_clause_with_provenance(corpus):
    chunks, ids = corpus
    idx = ChunkIndex(chunks)
    res = idx.search("gradual leakage seepage", RetrievalConfig(method="bm25", top_k=3),
                     doc_ids={ids["synthetic_home_policy.pdf"]})
    top = res.hits[0]
    assert (top.chunk.clause_id, top.chunk.page_number) == ("3.2", 3)
    assert top.rank == 1 and top.bm25_rank == 1 and top.vector_rank is None
    assert not res.degraded and res.notice is None and res.embedding_revision is None


def test_hybrid_without_model_degrades_visibly_to_bm25(corpus):
    chunks, ids = corpus
    idx = ChunkIndex(chunks)
    assert not idx.semantic_enabled
    res = idx.search("burst pipes", RetrievalConfig(method="hybrid_rrf"))
    assert res.degraded and res.method_used == "bm25" and res.method_requested == "hybrid_rrf"
    assert "semantic retrieval is disabled" in res.notice
    bm = idx.search("burst pipes", RetrievalConfig(method="bm25"))
    assert [h.chunk.chunk_id for h in res.hits] == [h.chunk.chunk_id for h in bm.hits]


def test_vector_without_model_raises_clear_error_not_silent_fallback(corpus):
    with pytest.raises(SemanticRetrievalDisabled, match="lexical-only"):
        ChunkIndex(corpus[0]).search("burst pipes", RetrievalConfig(method="vector"))


def test_empty_index_and_no_match(corpus):
    assert ChunkIndex([]).search("anything").hits == ()
    assert ChunkIndex(corpus[0]).search("zzzz qqqq", RetrievalConfig(method="bm25")).hits == ()


def test_document_scope_is_enforced(corpus):
    chunks, ids = corpus
    idx = ChunkIndex(chunks)
    fr = ids["synthetic_home_policy_fr.pdf"]
    res = idx.search("incendie foudre explosion", RetrievalConfig(method="bm25", top_k=10),
                     doc_ids={fr})
    assert res.hits and all(h.chunk.doc_id == fr for h in res.hits)
    other = idx.search("incendie", RetrievalConfig(method="bm25"),
                       doc_ids={ids["synthetic_travel_policy.pdf"]})
    assert other.hits == ()  # a clause from a non-selected document never leaks in


def test_accented_french_query_retrieves_unaccented_form(corpus):
    chunks, ids = corpus
    idx = ChunkIndex(chunks)
    fr = {ids["synthetic_home_policy_fr.pdf"]}
    a = idx.search("dégât des eaux", RetrievalConfig(method="bm25"), doc_ids=fr)
    b = idx.search("DEGAT DES EAUX", RetrievalConfig(method="bm25"), doc_ids=fr)
    assert [h.chunk.chunk_id for h in a.hits] == [h.chunk.chunk_id for h in b.hits]
    assert a.hits[0].chunk.clause_id in {"1.2", "2.2"}


def test_german_eszett_query(corpus):
    chunks, ids = corpus
    res = ChunkIndex(chunks).search("Verschleiss", RetrievalConfig(method="bm25"),
                                    doc_ids={ids["synthetic_home_policy_de.pdf"]})
    assert res.hits[0].chunk.clause_id == "3.1"


def test_exact_clause_id_retrieval_with_page(corpus):
    chunks, ids = corpus
    res = ChunkIndex(chunks).search("clause 4.3", RetrievalConfig(method="bm25"),
                                    doc_ids={ids["synthetic_home_policy.pdf"]})
    assert (res.hits[0].chunk.clause_id, res.hits[0].chunk.page_number) == ("4.3", 4)


# ---------- vector / hybrid code paths with a fake embedder ----------
def test_vector_and_hybrid_paths_run_and_report_ranks(corpus):
    chunks, _ = corpus
    idx = ChunkIndex(chunks, embedder=FakeEmbedder())
    assert idx.semantic_enabled
    v = idx.search("burst pipes", RetrievalConfig(method="vector", top_k=5))
    assert v.method_used == "vector" and not v.degraded and len(v.hits) == 5
    assert all(h.vector_rank is not None for h in v.hits)
    assert v.embedding_revision == "fake-rev"
    h = idx.search("burst pipes", RetrievalConfig(method="hybrid_rrf", top_k=5))
    assert h.method_used == "hybrid_rrf" and not h.degraded
    scores = [x.score for x in h.hits]
    assert scores == sorted(scores, reverse=True)
    assert any(x.bm25_rank is not None and x.vector_rank is not None for x in h.hits)


def test_hybrid_fusion_keeps_the_lexical_winner_even_when_vectors_ignore_it(corpus):
    chunks, ids = corpus
    idx = ChunkIndex(chunks, embedder=FakeEmbedder())
    scope = {ids["synthetic_home_policy.pdf"]}
    bm = idx.search("clause 4.3", RetrievalConfig(method="bm25", top_k=1), doc_ids=scope)
    assert bm.hits[0].chunk.clause_id == "4.3"
    hy = idx.search("clause 4.3", RetrievalConfig(method="hybrid_rrf", top_k=5, depth=48),
                    doc_ids=scope)
    assert "4.3" in [h.chunk.clause_id for h in hy.hits]
    top = next(h for h in hy.hits if h.chunk.clause_id == "4.3")
    assert top.bm25_rank == 1 and top.vector_rank is not None

def test_results_are_reproducible_across_runs_and_instances(corpus):
    chunks, _ = corpus
    cfg = RetrievalConfig(method="hybrid_rrf", top_k=8)
    runs = []
    for _ in range(2):
        idx = ChunkIndex(chunks, embedder=FakeEmbedder())
        r = idx.search("water damage from burst pipe", cfg)
        runs.append(([(h.chunk.chunk_id, h.score) for h in r.hits], r.config_fingerprint,
                     r.corpus_fingerprint, r.query_sha256))
    assert runs[0] == runs[1]


def test_corpus_fingerprint_changes_when_text_changes(corpus):
    chunks, _ = corpus
    assert corpus_fingerprint(chunks) == corpus_fingerprint(list(chunks))
    changed = [chunks[0].model_copy(update={"index_text": chunks[0].index_text + "!"})] + list(
        chunks[1:])
    assert corpus_fingerprint(changed) != corpus_fingerprint(chunks)


def test_result_converts_to_valid_evidence_and_audit_config(corpus):
    chunks, ids = corpus
    cfg = RetrievalConfig(method="bm25", top_k=2)
    res = ChunkIndex(chunks).search("excess per claim", cfg,
                                    doc_ids={ids["synthetic_home_policy.pdf"]})
    ev = res.hits[0].chunk.to_evidence(score=res.hits[0].score)
    assert ev.clause_id == "5.3" and ev.page_number == 5
    audit = AuditRecord(trace_id="t", retrieval=res.to_audit_config(cfg),
                        retrieved_chunk_ids=tuple(h.chunk.chunk_id for h in res.hits),
                        query_sha256=res.query_sha256)
    assert audit.retrieval.method == "bm25"
    assert "excess per claim" not in audit.model_dump_json()  # only the hash is recorded
    assert math.isclose(ev.score, res.hits[0].score)


def test_importing_retrieval_does_not_import_heavy_semantic_packages():
    import subprocess
    import sys

    code = ("import sys; import claims_engine.retrieval, claims_engine.eval_retrieval; "
            "assert 'sentence_transformers' not in sys.modules and 'torch' not in sys.modules")
    r = subprocess.run([sys.executable, "-I", "-c", f"import sys; sys.path.insert(0,'src'); {code}"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr