r"""End-to-end evaluation of the LangGraph workflow (held-out, adversarial, and the M2 cases).

Run:  python -m claims_engine.eval_workflow [--no-semantic]
Writes eval/m3/WORKFLOW_REPORT.md + eval/m3/workflow_results.json (only MEASURED numbers).
Everything is offline and free: the assessor is deterministic, no paid model is called.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import defaultdict

from .citations import validate_citations
from .embeddings import Embedder, EmbeddingUnavailable, load_embedder
from .eval_common import EVAL, load_docs, load_jsonl, sha256_file
from .support import AbstainPolicy
from .workflow import Workflow, WorkflowContext

C, X, I, R = ("potentially_covered", "potentially_excluded", "insufficient_evidence",
              "human_review_required")
VERDICTS = {C, X}


def run_cases(wf: Workflow, ids: dict[str, str], cases: list[dict]) -> list[dict]:
    chunk_by_id = {c.chunk_id: c for c in wf.ctx.index.chunks}
    rows = []
    for c in cases:
        scope = [ids[f] for f in c["scope"]]
        t0 = time.perf_counter()
        res = wf.run({"query": c["query"], "doc_ids": scope})
        ms = (time.perf_counter() - t0) * 1000
        a = res.assessment
        cited = [] if a is None else [*a.supporting_clauses, *a.exclusions_and_limitations]
        errs: list[str] = []
        if a is not None:  # independent re-validation against everything in scope
            pool = {k: v for k, v in chunk_by_id.items() if v.doc_id in scope}
            errs = [str(e) for e in validate_citations(a, pool, scope, wf.ctx.registry)]
        leaked = [e.chunk_id for e in (*res.retrieved, *cited) if e.doc_id not in scope]
        audit_json = res.audit.model_dump_json()
        rows.append({
            "id": c["id"], "category": c["category"], "lang": c["lang"], "kind": res.kind.value,
            "status": a.status.value if a else None, "primary": c.get("primary"),
            "acceptable": c.get("acceptable"), "relevant": c.get("relevant", []),
            "cited": [f"{wf.ctx.registry[e.doc_id].filename}#{e.clause_id}" for e in cited],
            "flags": list(res.audit.guardrail_flags), "path": list(res.audit.node_path),
            "priority": res.review_priority, "notices": list(res.notices),
            "citation_errors": errs, "leaked": leaked, "ms": ms,
            "query_text_in_audit": c["query"] in audit_json, "expect_flag": c.get("expect_flag")})
    return rows


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"n": 0}
    emitted = [r for r in rows if r["status"] in VERDICTS]
    exp_verdict = [r for r in rows if r["primary"] in VERDICTS]
    exp_abstain = [r for r in rows if r["primary"] in (I, R)]
    wrong_dir = [r for r in emitted if r["primary"] in VERDICTS and r["status"] != r["primary"]]
    unsupported = [r for r in emitted if r["status"] not in (r["acceptable"] or [])]
    return {
        "n": n,
        "status_accuracy": sum(r["status"] == r["primary"] for r in rows) / n,
        "acceptable_rate": sum(r["status"] in (r["acceptable"] or []) for r in rows) / n,
        "verdict_rate": len(emitted) / n,
        "verdict_coverage_on_verdict_cases": (sum(r["status"] in VERDICTS for r in exp_verdict) / len(exp_verdict)
                                              if exp_verdict else None),
        "unsupported_verdict_rate": len(unsupported) / n, "unsupported_ids": [r["id"] for r in unsupported],
        "wrong_direction": len(wrong_dir), "wrong_direction_ids": [r["id"] for r in wrong_dir],
        "abstention_quality": (sum(r["status"] in (r["acceptable"] or []) for r in exp_abstain) / len(exp_abstain)
                               if exp_abstain else None),
        "n_expected_abstain": len(exp_abstain),
        "over_abstention": (sum(r["status"] in (I, R) and r["status"] not in (r["acceptable"] or []) for r in exp_verdict)
                            / len(exp_verdict) if exp_verdict else None),
        "citation_error_cases": sum(bool(r["citation_errors"]) for r in rows),
        "scope_leaks": sum(len(r["leaked"]) for r in rows),
        "query_text_in_audit": sum(r["query_text_in_audit"] for r in rows),
        "mean_ms": statistics.fmean(r["ms"] for r in rows),
    }


def m2_system_view(rows: list[dict]) -> dict:
    """Same M2 cases, judged at SYSTEM level: did it cite only relevant clauses, abstain, or cite wrong?"""
    ans = [r for r in rows if r["relevant"]]
    un = [r for r in rows if not r["relevant"]]
    def rel(r): return {x for x in r["relevant"]}
    cited_ok = [r for r in ans if r["status"] in VERDICTS and r["cited"] and set(r["cited"]) <= rel(r)]
    cited_off = [r for r in ans if r["status"] in VERDICTS and r["cited"] and not set(r["cited"]) <= rel(r)]
    escalated = [r for r in ans if r["status"] in (I, R)]
    return {"answerable": len(ans), "verdict_with_only_relevant_citations": len(cited_ok),
            "verdict_with_off_target_citation": len(cited_off), "ids_off_target": [r["id"] for r in cited_off],
            "abstained_or_escalated": len(escalated), "unanswerable": len(un),
            "unanswerable_given_verdict": sum(r["status"] in VERDICTS for r in un),
            "unanswerable_abstained": sum(r["status"] in (I, R) for r in un)}


def by_category(rows: list[dict]) -> dict[str, dict]:
    g: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        g[r["category"]].append(r)
    return {k: summarize(v) for k, v in sorted(g.items())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-semantic", action="store_true")
    a = ap.parse_args()
    embedder: Embedder | None = None
    if not a.no_semantic:
        try:
            embedder = load_embedder()
        except EmbeddingUnavailable as exc:
            print("semantic mode skipped:", exc)
    docs = load_docs("policies", "heldout", "adversarial")
    ids = {d.filename: d.doc_id for d in docs}
    policy = AbstainPolicy.load()
    ho = load_jsonl(EVAL / "heldout_cases.jsonl")
    adv = load_jsonl(EVAL / "adversarial_cases.jsonl")
    m2_cases = [json.loads(x) for x in (EVAL / "baseline_m2" / "retrieval_cases.jsonl").read_text("utf-8").splitlines() if x.strip()]
    for c in m2_cases:  # adapt old format -> new
        f = c["scope"][0]
        c["relevant"] = [f"{f}#{r}" for r in c["relevant"]]
        c["primary"], c["acceptable"] = None, None
    modes: dict[str, Embedder | None] = {"lexical-only": None}
    if embedder is not None:
        modes["semantic (hybrid)"] = embedder
    out: dict = {"date": time.strftime("%Y-%m-%d"), "policy": policy.__dict__, "modes": {},
                 "inputs": {n: sha256_file(EVAL / n) for n in ("heldout_cases.jsonl", "adversarial_cases.jsonl",
                                                                "calibration_cases.jsonl")}}
    for mode, emb in modes.items():
        ctx = WorkflowContext.from_documents(docs, embedder=emb, stopwords=False, policy=policy)
        wf = Workflow(ctx)
        h_rows, a_rows, m_rows = run_cases(wf, ids, ho), run_cases(wf, ids, adv), run_cases(wf, ids, m2_cases)
        again = run_cases(wf, ids, ho)
        out["modes"][mode] = {
            "heldout": {"overall": summarize(h_rows), "by_category": by_category(h_rows), "rows": h_rows},
            "adversarial": {"overall": summarize(a_rows), "by_category": by_category(a_rows), "rows": a_rows},
            "m2_cases_system_view": m2_system_view(m_rows), "m2_rows": m_rows,
            "deterministic": [(r["id"], r["status"], r["cited"]) for r in h_rows] ==
                             [(r["id"], r["status"], r["cited"]) for r in again]}
    (EVAL / "m3").mkdir(exist_ok=True)
    (EVAL / "m3" / "workflow_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8", newline="\n")

    def p(x): return "-" if x is None else f"{x:.3f}"
    L = ["# Workflow evaluation (generated; measured numbers only)", "",
         f"- Abstain policy `{policy.version}`: tau_lex={policy.tau_lex}, tau_sem={policy.tau_sem}. {policy.note}",
         "- Held-out = not used to choose thresholds/variants. NOT blind: same author wrote policies, cases, cues. See eval/PREREGISTRATION.md.",
         "- Assessor: deterministic rules, offline, $0. No LLM involved anywhere.", ""]
    for mode, d in out["modes"].items():
        for setname in ("heldout", "adversarial"):
            o = d[setname]["overall"]
            L += [f"## {mode} - {setname} (n={o['n']})", "",
                  f"- status accuracy (== primary label): {p(o['status_accuracy'])}; acceptable-status rate: {p(o['acceptable_rate'])}",
                  f"- verdicts emitted: {p(o['verdict_rate'])}; coverage on cases whose label is a verdict: {p(o['verdict_coverage_on_verdict_cases'])}",
                  f"- **unsupported verdict rate: {p(o['unsupported_verdict_rate'])}** {o['unsupported_ids']}; wrong-direction verdicts: {o['wrong_direction']} {o['wrong_direction_ids']}",
                  f"- abstention quality (expected-abstain cases handled acceptably): {p(o['abstention_quality'])} (n={o['n_expected_abstain']}); over-abstention on verdict cases: {p(o['over_abstention'])}",
                  f"- independent citation re-validation failures: {o['citation_error_cases']}; cross-document leaks: {o['scope_leaks']}; query text found in audit record: {o['query_text_in_audit']}",
                  f"- mean latency: {o['mean_ms']:.1f} ms; estimated cost per assessment: $0 (no paid calls)", "",
                  "| category | n | acceptable | verdict coverage | unsupported | abstention quality |", "|---|---|---|---|---|---|"]
            for k, s in d[setname]["by_category"].items():
                L.append(f"| {k} | {s['n']} | {p(s['acceptable_rate'])} | {p(s['verdict_coverage_on_verdict_cases'])} | "
                         f"{p(s['unsupported_verdict_rate'])} | {p(s['abstention_quality'])} |")
            L.append("")
        ar = [r for r in d["adversarial"]["rows"] if r["expect_flag"]]
        L += [f"### {mode}: injection screen on adversarial cases that expect a flag: "
              f"{sum(bool(r['flags']) for r in ar)}/{len(ar)} flagged", ""]
        byp = [r for r in d["adversarial"]["rows"] if r["category"] == "injection_bypass"]
        L += [f"Paraphrased injections the keyword screen did NOT flag: {sum(not r['flags'] for r in byp)}/{len(byp)}; "
              f"outcomes: {[r['status'] for r in byp]} (no verdict was emitted: the assessor is deterministic and ignores instructions).", ""]
        s = d["m2_cases_system_view"]
        L += [f"### {mode}: the 52 M2 cases through the full workflow (system-level view)", "",
              f"- answerable ({s['answerable']}): verdict with only relevant citations {s['verdict_with_only_relevant_citations']}; "
              f"verdict with an off-target citation {s['verdict_with_off_target_citation']} {s['ids_off_target']}; abstained/escalated {s['abstained_or_escalated']}",
              f"- unanswerable ({s['unanswerable']}): given a verdict {s['unanswerable_given_verdict']}; abstained {s['unanswerable_abstained']}",
              f"- deterministic re-run identical: {d['deterministic']}", ""]
        rows = {r["id"]: r for r in d["m2_rows"]}
        L += ["M2 failure review (Q18/Q47 = hybrid failures; Q50-52 = unanswerable): " + "; ".join(
            f"{q}: {rows[q]['status']} cited={rows[q]['cited']}" for q in ("Q18", "Q47", "Q50", "Q51", "Q52") if q in rows), ""]
    (EVAL / "m3" / "WORKFLOW_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()