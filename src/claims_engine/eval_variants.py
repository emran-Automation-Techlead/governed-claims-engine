"""Retrieval-variant comparison (stopwords / subwords) and reproduction of the frozen M2 baseline.

Run (venv for the semantic arms):  python -m claims_engine.eval_variants [--no-semantic]
Writes eval/m3/VARIANTS_REPORT.md + eval/m3/variants_results.json. The frozen M2 files are only READ.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .bm25 import analyze, make_analyzer
from .embeddings import Embedder, EmbeddingUnavailable, load_embedder
from .eval_common import (
    EVAL,
    chunks_of,
    load_docs,
    load_jsonl,
    mean,
    ranked_keys,
    relevant_keys,
    score_keys,
)
from .eval_retrieval import build_corpus, load_cases, run_arm
from .retrieval import ChunkIndex, RetrievalConfig

VARIANTS = {
    "M2 analyzer (baseline)": analyze,
    "+ stopwords": make_analyzer(stopwords=True),
    "+ stopwords + subwords": make_analyzer(stopwords=True, subwords=True),
    "+ subwords only": make_analyzer(subwords=True),
}


def heldout_rows(index: ChunkIndex, ids: dict[str, str], cases: list[dict], method: str) -> list[dict]:
    rows = []
    for c in cases:
        scope = {ids[f] for f in c["scope"]}
        res = index.search(c["query"], RetrievalConfig(method=method, top_k=10), doc_ids=scope)
        ranked = ranked_keys([h.chunk for h in res.hits])
        row = {"id": c["id"], "category": c["category"], "n_results": len(res.hits),
               "top": [f"{k[1]}" for k in ranked[:5]]}
        if c["relevant"]:
            row.update(score_keys(ranked, relevant_keys(c)))
            row["relevant"] = [r.split("#")[1] for r in c["relevant"]]
        rows.append(row)
    return rows


def summarize(rows: list[dict]) -> dict:
    ans = [r for r in rows if "rr" in r]
    return {"n": len(ans), "hit@5": mean(ans, "hit@5"), "recall@3": mean(ans, "recall@3"),
            "recall@1": mean(ans, "recall@1"), "MRR": mean(ans, "rr"),
            "spurious_on_unanswerable": sum(1 for r in rows if "rr" not in r and r["n_results"]),
            "n_unanswerable": sum(1 for r in rows if "rr" not in r)}


def _hybrid_scores(idx: ChunkIndex, ids: dict[str, str], cases: list[dict], k: int, depth: int) -> dict:
    cfg = RetrievalConfig(method="hybrid_rrf", top_k=10, rrf_k=k, depth=depth)
    rows = []
    for c in cases:
        if not c["relevant"]:
            continue
        r = idx.search(c["query"], cfg, doc_ids={ids[f] for f in c["scope"]})
        rows.append(score_keys(ranked_keys([h.chunk for h in r.hits]), relevant_keys(c)))
    return {"hit@5": mean(rows, "hit@5"), "recall@3": mean(rows, "recall@3")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-semantic", action="store_true")
    a = ap.parse_args()
    embedder: Embedder | None = None
    if not a.no_semantic:
        try:
            embedder = load_embedder()
        except EmbeddingUnavailable as exc:
            print("semantic arms skipped:", exc)
    methods = ["bm25"] + (["hybrid_rrf", "vector"] if embedder else [])

    # ---- M2 set on the original 4-document corpus, via the UNCHANGED M2 code path ----
    m2_cases = load_cases(EVAL / "retrieval_cases.jsonl")
    m2_chunks, m2_ids = build_corpus(Path("data/policies"))
    frozen = json.loads((EVAL / "baseline_m2" / "retrieval_results.json").read_text("utf-8"))
    frozen_by_arm = {x["arm"]: x["overall"] for x in frozen["arms"]}
    out: dict = {"date": time.strftime("%Y-%m-%d"), "embedding": embedder.revision if embedder else None,
                 "m2": {}, "heldout": {}, "reproduction": {}}
    for vname, an in VARIANTS.items():
        idx = ChunkIndex(m2_chunks, embedder=embedder, analyzer=an)
        out["m2"][vname] = {}
        for m in methods:
            arm = run_arm(f"{vname}/{m}", idx, m, m2_cases, m2_ids)
            o = arm["overall"]
            out["m2"][vname][m] = {"n": o["n"], "hit@5": o["hit@5"], "recall@3": o["recall@3"],
                                    "recall@1": o["recall@1"], "MRR": o["MRR"],
                                    "spurious_on_unanswerable": sum(1 for u in arm["unanswerable"] if u["n_results"]),
                                    "n_unanswerable": len(arm["unanswerable"]),
                                    "failures": [f"{r['id']}" for r in arm["failures_hit@5"]]}
    # reproduction check: baseline analyzer must equal the frozen published numbers
    for m, arm_name in (("bm25", "bm25 (multilingual)"), ("hybrid_rrf", "hybrid RRF"), ("vector", "vector")):
        if m in out["m2"]["M2 analyzer (baseline)"] and arm_name in frozen_by_arm:
            cur, old = out["m2"]["M2 analyzer (baseline)"][m], frozen_by_arm[arm_name]
            out["reproduction"][m] = all(abs(cur[k] - old[kk]) < 1e-9 for k, kk in
                                         (("hit@5", "hit@5"), ("recall@3", "recall@3"), ("MRR", "MRR")))

    # ---- held-out retrieval on policies + heldout documents ----
    ho_docs = load_docs("policies", "heldout")
    ho_chunks = chunks_of(ho_docs)
    ho_ids = {d.filename: d.doc_id for d in ho_docs}
    ho_cases = load_jsonl(EVAL / "heldout_cases.jsonl")
    for vname, an in VARIANTS.items():
        idx = ChunkIndex(ho_chunks, embedder=embedder, analyzer=an)
        out["heldout"][vname] = {}
        for m in methods:
            rows = heldout_rows(idx, ho_ids, ho_cases, m)
            comp = [r for r, c in zip(rows, ho_cases, strict=True)
                    if c["category"] == "german_compound" and "rr" in r]
            rest = [r for r, c in zip(rows, ho_cases, strict=True) if c["category"] != "german_compound"]
            out["heldout"][vname][m] = {"all": summarize(rows), "german_compound": summarize(comp),
                                         "non_compound": summarize(rest),
                                         "failed_ids": [r["id"] for r in rows if "rr" in r and r["hit@5"] == 0.0]}

    out["rrf_sensitivity"] = {}
    if embedder:  # measurement only: defaults (k=60, depth=20) are NOT changed by this
        m2_idx = ChunkIndex(m2_chunks, embedder=embedder, analyzer=analyze)
        ho_idx = ChunkIndex(ho_chunks, embedder=embedder, analyzer=analyze)
        m2_norm = [{**c, "relevant": [f"{c['scope'][0]}#{r}" for r in c["relevant"]]} for c in m2_cases]
        for k in (10, 60, 200):
            for depth in (5, 20):
                out["rrf_sensitivity"][f"k={k},depth={depth}"] = {
                    "m2": _hybrid_scores(m2_idx, m2_ids, m2_norm, k, depth),
                    "heldout": _hybrid_scores(ho_idx, ho_ids, ho_cases, k, depth)}

    (EVAL / "m3").mkdir(exist_ok=True)
    (EVAL / "m3" / "variants_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8", newline="\n")

    def f(x: float) -> str:
        return f"{x:.3f}"

    L = ["# Retrieval variants (generated)", "",
         f"Embedding: {out['embedding'] or 'NOT RUN'}. Baseline reproduction (M2 analyzer vs frozen M2 numbers): {out['reproduction']}",
         "", "## M2 cases (49 answerable + 3 unanswerable), original 4-document corpus", "",
         "| variant | method | hit@5 | Recall@3 | Recall@1 | MRR | spurious/unans. | failures |", "|---|---|---|---|---|---|---|---|"]
    for v, ms in out["m2"].items():
        for m, s in ms.items():
            L.append(f"| {v} | {m} | {f(s['hit@5'])} | {f(s['recall@3'])} | {f(s['recall@1'])} | {f(s['MRR'])} | "
                     f"{s['spurious_on_unanswerable']}/{s['n_unanswerable']} | {', '.join(s['failures'])} |")
    L += ["", "## Held-out cases (7-document corpus, per-case document scope)", "",
          "| variant | method | hit@5 all | Recall@3 all | spurious/unans. | hit@5 compound (n=7) | hit@5 non-compound | failed ids |",
          "|---|---|---|---|---|---|---|---|"]
    for v, ms in out["heldout"].items():
        for m, s in ms.items():
            L.append(f"| {v} | {m} | {f(s['all']['hit@5'])} | {f(s['all']['recall@3'])} | "
                     f"{s['all']['spurious_on_unanswerable']}/{s['all']['n_unanswerable']} | "
                     f"{f(s['german_compound']['hit@5'])} | {f(s['non_compound']['hit@5'])} | "
                     f"{', '.join(s['failed_ids'])} |")
    if out["rrf_sensitivity"]:
        L += ["", "## RRF sensitivity (hybrid, M2 analyzer) - measurement only, defaults unchanged", "",
              "| setting | M2 hit@5 | M2 Recall@3 | held-out hit@5 | held-out Recall@3 |", "|---|---|---|---|---|"]
        for name, r in out["rrf_sensitivity"].items():
            L.append(f"| {name} | {f(r['m2']['hit@5'])} | {f(r['m2']['recall@3'])} | "
                     f"{f(r['heldout']['hit@5'])} | {f(r['heldout']['recall@3'])} |")
    (EVAL / "m3" / "VARIANTS_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
