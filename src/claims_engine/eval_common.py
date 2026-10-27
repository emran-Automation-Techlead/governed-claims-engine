"""Shared helpers for the Milestone-3 evaluations (new case format: relevant = "file#clause")."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from .chunking import chunk_document
from .config import PROJECT_ROOT
from .ingestion import ingest_pdf_path
from .schemas import Chunk, DocumentRecord

DATA = PROJECT_ROOT / "data"
EVAL = PROJECT_ROOT / "eval"
KS = (1, 3, 5)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows = [json.loads(x) for x in path.read_text("utf-8").splitlines() if x.strip()]
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate ids in {path.name}")
    return rows


def load_docs(*subdirs: str) -> list[DocumentRecord]:
    docs: list[DocumentRecord] = []
    for sd in subdirs:
        docs.extend(ingest_pdf_path(p) for p in sorted((DATA / sd).glob("*.pdf")))
    return docs


def chunks_of(docs: Sequence[DocumentRecord]) -> list[Chunk]:
    out: list[Chunk] = []
    for d in docs:
        out.extend(chunk_document(d))
    return out


def relevant_keys(case: dict) -> set[tuple[str, str]]:
    return {tuple(r.split("#", 1)) for r in case["relevant"]}  # type: ignore[misc]


def ranked_keys(chunks: Sequence[Chunk]) -> list[tuple[str, str | None]]:
    seen: list[tuple[str, str | None]] = []
    for c in chunks:
        k = (c.filename, c.clause_id)
        if k not in seen:
            seen.append(k)
    return seen


def score_keys(ranked: Sequence[tuple[str, str | None]], rel: set[tuple[str, str]]) -> dict:
    first = next((i for i, k in enumerate(ranked, 1) if k in rel), None)
    out: dict = {"first_rank": first, "rr": (1.0 / first) if first else 0.0}
    for k in KS:
        got = len(rel & set(ranked[:k]))
        out[f"recall@{k}"] = got / len(rel)
        out[f"hit@{k}"] = 1.0 if got else 0.0
    return out


def mean(rows: Sequence[dict], key: str) -> float:
    return sum(r[key] for r in rows) / len(rows) if rows else float("nan")


def rule_of_three(n: int) -> float:
    """Approx. 95 % upper bound on a rate after 0 events in n trials."""
    return min(1.0, 3.0 / n) if n else 1.0