"""Evidence-support scoring and the abstention policy.

A retrieved chunk is "supported" for a query when it clears the calibrated gate:
    lexical coverage >= tau_lex      OR      (cosine >= tau_sem when an embedder is loaded)
Lexical coverage = IDF-weighted share of the query's content terms that appear in the chunk
(terms unseen anywhere in the corpus count with the maximum IDF, so they lower coverage).
It is interpretable, deterministic, works without any model, and is comparable across queries
(unlike raw BM25 scores).

The thresholds are NOT hard-coded guesses: `calibrate.py` derives them from a labelled
calibration set and writes calibration/abstain_policy.json. If that file is missing the policy
FAILS CLOSED (nothing is ever "supported" -> always abstain).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .bm25 import Analyzer, make_analyzer
from .config import PROJECT_ROOT
from .retrieval import ChunkIndex, RetrievedChunk
from .schemas import Chunk

POLICY_PATH = PROJECT_ROOT / "calibration" / "abstain_policy.json"
COVERAGE_ANALYZER: Analyzer = make_analyzer(stopwords=True, subwords=False)


@dataclass(frozen=True)
class AbstainPolicy:
    version: str = "fail-closed"
    tau_lex: float = 1.01  # unreachable -> never supported
    tau_sem: float | None = None  # None -> semantic evidence is never accepted
    note: str = "no calibration file found: failing closed"

    @classmethod
    def load(cls, path: Path | None = None) -> AbstainPolicy:
        p = path or POLICY_PATH
        if not p.is_file():
            return cls()
        d = json.loads(p.read_text("utf-8"))
        return cls(version=d["version"], tau_lex=float(d["tau_lex"]),
                   tau_sem=None if d.get("tau_sem") is None else float(d["tau_sem"]),
                   note=d.get("note", ""))


@dataclass(frozen=True)
class ScoredChunk:
    hit: RetrievedChunk
    lex_cov: float
    cosine: float | None
    supported: bool
    continuation: tuple[Chunk, ...] = ()

    @property
    def chunk(self) -> Chunk:
        return self.hit.chunk


def lexical_coverage(query: str, chunk: Chunk, index: ChunkIndex) -> float:
    q_terms = set(COVERAGE_ANALYZER(query))
    if not q_terms:
        return 0.0
    c_terms = set(COVERAGE_ANALYZER(chunk.index_text))
    top = index.max_idf
    total = matched = 0.0
    for t in q_terms:
        w = index.term_idf(t)
        w = top if w is None else w
        total += w
        if t in c_terms:
            matched += w
    return matched / total if total else 0.0


def score_hit(query: str, hit: RetrievedChunk, index: ChunkIndex,
              policy: AbstainPolicy) -> ScoredChunk:
    cov = lexical_coverage(query, hit.chunk, index)
    sem_ok = policy.tau_sem is not None and hit.cosine is not None and hit.cosine >= policy.tau_sem
    return ScoredChunk(hit, cov, hit.cosine, cov >= policy.tau_lex or sem_ok,
                       index.continuations(hit.chunk))