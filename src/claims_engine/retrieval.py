"""Hybrid retrieval: BM25 + optional vector search, combined with Reciprocal Rank Fusion.

RRF:  score(d) = sum over rankers r of  1 / (k + rank_r(d))      (rank is 1-based, k = 60 default)
It uses ranks only, so BM25 scores and cosine similarities need no calibration.

Reproducibility: every result carries the config fingerprint, the corpus fingerprint and the
embedding revision. All tie-breaks are deterministic (score desc, then chunk order).
Without an embedder, `hybrid_rrf` degrades to BM25 and SAYS SO (`degraded`, `notice`);
an explicit `vector` request raises SemanticRetrievalDisabled instead of silently substituting.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Sequence
from dataclasses import asdict, dataclass

import numpy as np

from .bm25 import Analyzer, BM25Index, analyze
from .config import BM25Params
from .embeddings import Embedder
from .schemas import Chunk, RetrievalConfigRecord

METHODS = ("bm25", "vector", "hybrid_rrf")


class SemanticRetrievalDisabled(RuntimeError):
    pass


@dataclass(frozen=True)
class RetrievalConfig:
    method: str = "hybrid_rrf"
    top_k: int = 5
    rrf_k: int = 60
    depth: int = 20  # how many candidates each ranker contributes to fusion
    bm25_k1: float = 1.5
    bm25_b: float = 0.75

    def __post_init__(self) -> None:
        if self.method not in METHODS:
            raise ValueError(f"method must be one of {METHODS}")
        if self.top_k < 1 or self.depth < 1 or self.rrf_k < 1:
            raise ValueError("top_k, depth and rrf_k must be >= 1")

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:16]


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float
    rank: int  # 1-based position in the final list
    bm25_rank: int | None = None
    vector_rank: int | None = None
    cosine: float | None = None  # query-chunk cosine similarity when an embedder is loaded


@dataclass(frozen=True)
class RetrievalResult:
    query_sha256: str
    hits: tuple[RetrievedChunk, ...]
    method_requested: str
    method_used: str
    degraded: bool
    notice: str | None
    config_fingerprint: str
    corpus_fingerprint: str
    embedding_revision: str | None

    def to_audit_config(self, cfg: RetrievalConfig) -> RetrievalConfigRecord:
        return RetrievalConfigRecord(
            method=self.method_used, top_k=cfg.top_k,
            params={"rrf_k": cfg.rrf_k, "depth": cfg.depth, "bm25_k1": cfg.bm25_k1,
                    "bm25_b": cfg.bm25_b, "config_fp": self.config_fingerprint,
                    "corpus_fp": self.corpus_fingerprint,
                    "embedding_revision": self.embedding_revision or "none"})


def rrf_fuse(rankings: Sequence[Sequence[int]], *, k: int = 60,
             top_k: int | None = None) -> list[tuple[int, float]]:
    """Fuse ranked lists of item ids. Ties: higher score, then best individual rank, then id."""
    if k < 1:
        raise ValueError("k must be >= 1")
    score: dict[int, float] = {}
    best: dict[int, int] = {}
    for ranking in rankings:
        for pos, item in enumerate(ranking, start=1):
            score[item] = score.get(item, 0.0) + 1.0 / (k + pos)
            best[item] = min(best.get(item, pos), pos)
    fused = sorted(score, key=lambda i: (-score[i], best[i], i))
    out = [(i, score[i]) for i in fused]
    return out[:top_k] if top_k else out


def corpus_fingerprint(chunks: Sequence[Chunk]) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c.chunk_id.encode() + b"\0" + c.index_text.encode() + b"\0")
    return h.hexdigest()[:16]


class ChunkIndex:
    def __init__(self, chunks: Sequence[Chunk], embedder: Embedder | None = None,
                 bm25_params: BM25Params | None = None, analyzer: Analyzer = analyze) -> None:
        self.chunks = tuple(chunks)
        self.embedder = embedder
        self._bm25 = BM25Index([c.index_text for c in self.chunks], bm25_params, analyzer)
        self._vecs: np.ndarray | None = None
        if embedder is not None and self.chunks:
            self._vecs = np.asarray(embedder.encode([c.index_text for c in self.chunks]),
                                    dtype=np.float32)
        self.corpus_fp = corpus_fingerprint(self.chunks)
        self._by_id = {c.chunk_id: c for c in self.chunks}

    def continuations(self, chunk: Chunk) -> tuple[Chunk, ...]:
        """Following chunks that continue the SAME clause (page break or long-clause split)."""
        out: list[Chunk] = []
        nxt = self._by_id.get(chunk.next_chunk_id) if chunk.next_chunk_id else None
        while (nxt is not None and nxt.continues_previous and nxt.clause_id == chunk.clause_id
               and nxt.doc_id == chunk.doc_id):
            out.append(nxt)
            nxt = self._by_id.get(nxt.next_chunk_id) if nxt.next_chunk_id else None
        return tuple(out)

    def term_idf(self, term: str) -> float | None:
        return self._bm25.idf(term)

    @property
    def max_idf(self) -> float:
        return self._bm25.max_idf

    @property
    def semantic_enabled(self) -> bool:
        return self._vecs is not None or (self.embedder is not None and not self.chunks)

    def _allowed(self, doc_ids: Collection[str] | None) -> list[int]:
        if doc_ids is None:
            return list(range(len(self.chunks)))
        return [i for i, c in enumerate(self.chunks) if c.doc_id in doc_ids]

    def _bm25_rank(self, query: str, allowed: set[int]) -> list[int]:
        hits = self._bm25.search(query, max(1, self._bm25.n_docs))
        return [h.index for h in hits if h.index in allowed]

    def _vector_rank(self, query: str, allowed: set[int]) -> list[int]:
        if self.embedder is None or self._vecs is None:
            raise SemanticRetrievalDisabled("vector ranking requested without a loaded embedding model")
        q = np.asarray(self.embedder.encode([query])[0], dtype=np.float32)
        sims = self._vecs @ q
        order = sorted(allowed, key=lambda i: (-float(sims[i]), i))
        return order

    def search(self, query: str, config: RetrievalConfig | None = None, *,
               doc_ids: Collection[str] | None = None) -> RetrievalResult:
        cfg = config or RetrievalConfig()
        allowed = set(self._allowed(doc_ids))
        used, notice = cfg.method, None
        have_vec = self._vecs is not None
        if cfg.method in ("vector", "hybrid_rrf") and not have_vec:
            if cfg.method == "vector":
                raise SemanticRetrievalDisabled(
                    "semantic retrieval is disabled: no embedding model is loaded "
                    "(lexical-only mode). Use method='bm25' or fetch the model deliberately.")
            used = "bm25"
            notice = ("semantic retrieval is disabled (no embedding model loaded); "
                      "results are lexical-only BM25")
        bm = self._bm25_rank(query, allowed) if used in ("bm25", "hybrid_rrf") else []
        vec = self._vector_rank(query, allowed) if used in ("vector", "hybrid_rrf") else []
        bm_pos = {i: r for r, i in enumerate(bm, 1)}
        vec_pos = {i: r for r, i in enumerate(vec, 1)}
        if used == "bm25":
            scored = [(i, self._bm25.score(query, i)) for i in bm[: cfg.top_k]]
        elif used == "vector":
            q = np.asarray(self.embedder.encode([query])[0], dtype=np.float32)  # type: ignore[union-attr]
            if self._vecs is None:
                raise SemanticRetrievalDisabled("vector ranking requested without a loaded embedding model")
            scored = [(i, float(self._vecs[i] @ q)) for i in vec[: cfg.top_k]]
        else:
            scored = rrf_fuse([bm[: cfg.depth], vec[: cfg.depth]], k=cfg.rrf_k, top_k=cfg.top_k)
        qv = None
        if have_vec and self.embedder is not None:
            qv = np.asarray(self.embedder.encode([query])[0], dtype=np.float32)
        hits = tuple(
            RetrievedChunk(self.chunks[i], s, r, bm_pos.get(i), vec_pos.get(i),
                           float(self._vecs[i] @ qv) if qv is not None and self._vecs is not None
                           else None)
            for r, (i, s) in enumerate(scored, 1))
        return RetrievalResult(
            query_sha256=hashlib.sha256(query.encode()).hexdigest(), hits=hits,
            method_requested=cfg.method, method_used=used, degraded=used != cfg.method,
            notice=notice, config_fingerprint=cfg.fingerprint(), corpus_fingerprint=self.corpus_fp,
            embedding_revision=self.embedder.revision if (self.embedder and have_vec) else None)