r"""Derive the abstention thresholds from the labelled CALIBRATION set (never the held-out sets).

Run (venv, for the semantic threshold):  python -m claims_engine.calibrate [--no-semantic]
Rule (pre-registered in eval/PREREGISTRATION.md):
    tau = smallest grid value with ZERO false accepts on the unanswerable calibration cases,
    plus ONE grid step of safety margin (prefer abstention).
A case is "accepted" when any of the top-3 retrieved chunks is supported (clears the gate).
Writes calibration/abstain_policy.json and calibration/CALIBRATION_REPORT.md.
"""
from __future__ import annotations

import argparse
import json
import time

from .config import PROJECT_ROOT
from .embeddings import EmbeddingUnavailable, load_embedder
from .eval_common import (
    EVAL,
    chunks_of,
    load_docs,
    load_jsonl,
    relevant_keys,
    rule_of_three,
    sha256_file,
)
from .retrieval import ChunkIndex, RetrievalConfig
from .support import lexical_coverage

WINDOW = 3
LEX_GRID = [round(0.05 * i, 2) for i in range(1, 21)]  # 0.05 .. 1.00
SEM_GRID = [round(0.02 * i, 2) for i in range(5, 46)]  # 0.10 .. 0.90
OUT = PROJECT_ROOT / "calibration"


def collect(index: ChunkIndex, ids: dict[str, str], cases: list[dict], method: str) -> list[dict]:
    rows = []
    for c in cases:
        res = index.search(c["query"], RetrievalConfig(method=method, top_k=WINDOW),
                           doc_ids={ids[f] for f in c["scope"]})
        rel = relevant_keys(c)
        rows.append({"id": c["id"], "category": c["category"], "answerable": bool(rel),
                     "hits": [{"lex": lexical_coverage(c["query"], h.chunk, index), "cos": h.cosine,
                               "relevant": (h.chunk.filename, h.chunk.clause_id) in rel}
                              for h in res.hits]})
    return rows


def evaluate(rows: list[dict], tau_lex: float | None, tau_sem: float | None) -> dict:
    def supported(h: dict) -> bool:
        return ((tau_lex is not None and h["lex"] >= tau_lex)
                or (tau_sem is not None and h["cos"] is not None and h["cos"] >= tau_sem))
    ans = [r for r in rows if r["answerable"]]
    un = [r for r in rows if not r["answerable"]]
    good = sum(any(supported(h) and h["relevant"] for h in r["hits"]) for r in ans)
    wrong = sum(any(supported(h) for h in r["hits"]) and not any(supported(h) and h["relevant"]
                                                                 for h in r["hits"]) for r in ans)
    fa = [r["id"] for r in un if any(supported(h) for h in r["hits"])]
    return {"answer_rate": good / len(ans), "answered_wrong_only": wrong, "n_ans": len(ans),
            "false_accepts": len(fa), "false_accept_ids": fa, "n_unans": len(un)}


def pick(grid: list[float], fn) -> tuple[float | None, float | None]:
    """smallest grid value with zero false accepts; and that value + one step."""
    for i, t in enumerate(grid):
        if fn(t)["false_accepts"] == 0:
            return t, grid[min(i + 1, len(grid) - 1)]
    return None, None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-semantic", action="store_true")
    a = ap.parse_args()
    embedder = None
    if not a.no_semantic:
        try:
            embedder = load_embedder()
        except EmbeddingUnavailable as exc:
            print("semantic threshold skipped:", exc)
    docs = load_docs("policies")  # calibration cases only touch the 4 original documents
    ids = {d.filename: d.doc_id for d in docs}
    cases = load_jsonl(EVAL / "calibration_cases.jsonl")
    chunks = chunks_of(docs)
    lex_rows = collect(ChunkIndex(chunks), ids, cases, "bm25")
    zero_lex, tau_lex = pick(LEX_GRID, lambda t: evaluate(lex_rows, t, None))
    if tau_lex is None:
        tau_lex = 1.01  # nothing separates the classes: fail closed
    sem_rows, tau_sem, zero_sem = None, None, None
    if embedder is not None:
        sem_rows = collect(ChunkIndex(chunks, embedder=embedder), ids, cases, "hybrid_rrf")
        zero_sem, tau_sem = pick(SEM_GRID, lambda t: evaluate(sem_rows, tau_lex, t))
    n_unans = sum(1 for c in cases if not c["relevant"])
    policy = {
        "version": "cal-" + time.strftime("%Y-%m-%d") + "-v1", "tau_lex": tau_lex, "tau_sem": tau_sem,
        "note": (f"zero-false-accept threshold(s): lex={zero_lex}, sem={zero_sem}; +1 grid step margin; "
                 f"calibrated on {len(cases)} cases ({n_unans} unanswerable) over 4 synthetic policies; "
                 f"rule-of-three 95% upper bound on false-accept rate ~{rule_of_three(n_unans):.2f}"),
        "calibration_cases_sha256": sha256_file(EVAL / "calibration_cases.jsonl"),
        "retrieval_analyzer": "M2 baseline (stopwords/subwords not adopted for ranking)",
        "coverage_analyzer": "stopwords on, subwords off", "window": WINDOW}
    OUT.mkdir(exist_ok=True)
    (OUT / "abstain_policy.json").write_text(json.dumps(policy, indent=2), encoding="utf-8", newline="\n")

    def f(x): return f"{x:.3f}"
    L = ["# Abstention calibration (generated)", "",
         f"- Cases: {len(cases)} ({len(cases) - n_unans} answerable, {n_unans} unanswerable), 4 synthetic policies.",
         f"- Chosen: **tau_lex = {tau_lex}** (zero-false-accept value {zero_lex} + 1 step), "
         f"**tau_sem = {tau_sem}** (zero-false-accept value {zero_sem} + 1 step; null = semantic evidence not accepted).",
         f"- Rule-of-three 95 % upper bound on the false-accept rate with 0 observed in {n_unans}: ~{rule_of_three(n_unans):.0%}. "
         "Do not read this as a measured safety level.", "",
         "## Lexical gate sweep (BM25 top-3)", "", "| tau_lex | answer rate | answered-wrong-only | false accepts |", "|---|---|---|---|"]
    for t in LEX_GRID:
        e = evaluate(lex_rows, t, None)
        mark = " **<- chosen**" if t == tau_lex else ""
        L.append(f"| {t}{mark} | {f(e['answer_rate'])} | {e['answered_wrong_only']} | {e['false_accepts']}/{e['n_unans']} |")
    if sem_rows:
        L += ["", f"## Semantic gate sweep (hybrid top-3, tau_lex fixed at {tau_lex})", "",
              "| tau_sem | answer rate | answered-wrong-only | false accepts |", "|---|---|---|---|"]
        for t in SEM_GRID:
            e = evaluate(sem_rows, tau_lex, t)
            mark = " **<- chosen**" if t == tau_sem else ""
            L.append(f"| {t}{mark} | {f(e['answer_rate'])} | {e['answered_wrong_only']} | {e['false_accepts']}/{e['n_unans']} |")
        base = evaluate(sem_rows, tau_lex, None)
        L.append(f"\nLexical gate alone on hybrid top-3: answer rate {f(base['answer_rate'])}, "
                 f"false accepts {base['false_accepts']}/{base['n_unans']} {base['false_accept_ids']}")
    chosen = evaluate(lex_rows, tau_lex, None)
    L += ["", "## Chosen lexical threshold on the calibration set itself", "",
          f"answer rate {f(chosen['answer_rate'])}; false accepts {chosen['false_accepts']}/{chosen['n_unans']}.",
          "(This is the SAME data the threshold was fitted on - optimistic by construction. See the held-out report.)",
          "", "## Limitations", "",
          "- Few unanswerable cases; the zero-false-accept threshold is an upper-envelope of 28 queries, not a guarantee.",
          "- Coverage is lexical: paraphrases and cross-lingual queries score ~0 and are abstained on in lexical-only mode (by design: prefer abstention).",
          "- Calibrated on 4 short synthetic policies; thresholds will not transfer to long real policies without recalibration.",
          "- The one-step margin is a judgment call, not a statistically derived guard band."]
    (OUT / "CALIBRATION_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()