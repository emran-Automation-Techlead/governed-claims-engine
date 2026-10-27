"""In-house BM25 (Okapi) lexical index.

Score(q, d) = sum over query terms t of  IDF(t) * f(t,d)*(k1+1) / (f(t,d) + k1*(1-b+b*|d|/avgdl))
IDF(t) = ln( (N - n_t + 0.5) / (n_t + 0.5) + 1 )   (the non-negative "Lucene" variant)

Kept behind a tiny interface (`build` / `search`) so it can be swapped for `rank-bm25`
later if a measurable benefit appears. Deterministic: ties break by document index.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .config import BM25Params

# Unicode-aware: [^\W_] matches letters/digits in any script; clause ids (3.1, 4.2.1) and
# hyphenated words stay whole so exact references remain searchable.
_TOKEN = re.compile(r"[^\W_]+(?:[.\-][^\W_]+)*")
_LIGATURES = str.maketrans({"œ": "oe", "æ": "ae", "ø": "o", "đ": "d", "ł": "l"})
_LEGACY_TOKEN = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")

Analyzer = Callable[[str], list[str]]


def fold(text: str) -> str:
    """Case-fold and strip accents: 'Dégât' -> 'degat', 'Verschleiß' -> 'verschleiss'."""
    s = unicodedata.normalize("NFKD", text.casefold()).translate(_LIGATURES)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def tokenize(text: str) -> list[str]:
    """Accent-folded tokens (Milestone-1 behaviour preserved: nothing is dropped)."""
    return _TOKEN.findall(fold(text))


def analyze(text: str) -> list[str]:
    """Retrieval analyzer: `tokenize`, minus single letters (French elision l', d'), plus the
    parts of hyphenated words ('pre-existing' -> also 'pre', 'existing')."""
    out: list[str] = []
    for t in tokenize(text):
        if len(t) == 1 and not t.isdigit():
            continue
        out.append(t)
        if "-" in t and not t[0].isdigit():
            out.extend(p for p in t.split("-") if len(p) > 1)
    return out


def make_analyzer(*, stopwords: bool = False, subwords: bool = False) -> Analyzer:
    r"""Analyzer factory. `make_analyzer()` is exactly `analyze` (Milestone-2 behaviour).

    stopwords: drop EN/FR/DE function words (negations/conditions are protected, see stopwords.py).
    subwords:  for long tokens (>= 12 letters, e.g. German compounds) also emit overlapping
               5-letter fragments, prefixed "#", so "wasserschaden" can match
               "leitungswasserschaden". Experimental: adoption is decided by held-out evaluation.
    """
    from .stopwords import STOPWORDS

    def _analyzer(text: str) -> list[str]:
        out: list[str] = []
        for t in analyze(text):
            if stopwords and t in STOPWORDS:
                continue
            out.append(t)
            if subwords and len(t) >= 12 and t.isalpha():
                out.extend("#" + t[i:i + 5] for i in range(len(t) - 4))
        return out

    return _analyzer


def tokenize_legacy(text: str) -> list[str]:
    """Milestone-1 ASCII tokenizer, kept only to measure what the multilingual one fixes."""
    return _LEGACY_TOKEN.findall(text.lower())

@dataclass(frozen=True)
class Hit:
    index: int
    score: float


class BM25Index:
    def __init__(self, documents: Sequence[str], params: BM25Params | None = None,
                 analyzer: Analyzer = tokenize) -> None:
        self.params = params or BM25Params()
        self._analyze = analyzer
        self._tf: list[Counter[str]] = [Counter(analyzer(d)) for d in documents]
        self._len = [sum(c.values()) for c in self._tf]
        self.n_docs = len(self._tf)
        self._avgdl = (sum(self._len) / self.n_docs) if self.n_docs else 0.0
        df: Counter[str] = Counter()
        for c in self._tf:
            df.update(c.keys())
        self._idf = {
            t: math.log((self.n_docs - n + 0.5) / (n + 0.5) + 1.0) for t, n in df.items()
        }

    def idf(self, term: str) -> float | None:
        """IDF of a term, or None if the term never occurs in the corpus."""
        return self._idf.get(term)

    @property
    def max_idf(self) -> float:
        return max(self._idf.values(), default=0.0)

    def score(self, query: str, index: int) -> float:
        tf, dl = self._tf[index], self._len[index]
        k1, b = self.params.k1, self.params.b
        norm = k1 * (1 - b + b * dl / self._avgdl) if self._avgdl else k1
        total = 0.0
        for t in set(self._analyze(query)):
            f = tf.get(t, 0)
            if f:
                total += self._idf[t] * f * (k1 + 1) / (f + norm)
        return total

    def search(self, query: str, top_k: int = 5) -> list[Hit]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        hits = [Hit(i, s) for i in range(self.n_docs) if (s := self.score(query, i)) > 0.0]
        hits.sort(key=lambda h: (-h.score, h.index))
        return hits[:top_k]
