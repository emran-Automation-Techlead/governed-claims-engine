r"""LangGraph decision workflow: explicit, individually testable stages.

START -> validate_input --reject--> reject --------------------------------------------+
            | ok                                                                        |
         screen_query --flagged--> abstain ------------------------------+              |
            | clean                                                      |              |
         retrieve -> enforce_scope --violation--> abstain ---------------+              |
            | in scope                                                   |              |
         screen_evidence -> score_evidence --none supported / quarantined--> abstain ---+|
            | supported                                                  |             ||
         assess -> validate_citations --invalid, attempts left--> assess |             ||
            | valid        \--invalid, exhausted--> abstain -------------+             ||
         human_review_gate <------------------------------------------------------------+|
            |                                                                            |
          audit <-------------------------------------------------------------------------+
            |
           END

Offline by construction: no network or model call exists in any node (the optional embedder
only runs locally). Tracing env vars are forced off so LangChain/LangSmith never phones home.
Failures route to `abstain`, which converts them to a safe assessment; they never become verdicts.
"""
from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, TypedDict

from pydantic import ValidationError

for _k in ("LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING", "LANGCHAIN_TRACING"):
    os.environ[_k] = "false"

from langgraph.graph import END, START, StateGraph

from .assessor import AssessmentInput, Assessor, RuleAssessor
from .bm25 import make_analyzer
from .chunking import chunk_document
from .citations import DocInfo, validate_citations
from .embeddings import Embedder
from .guardrails import screen_text, strip_hidden
from .retrieval import ChunkIndex, RetrievalConfig, RetrievedChunk
from .review import AuditSink, audit_event
from .schemas import (
    Assessment,
    AssessmentStatus,
    AuditRecord,
    Chunk,
    ClaimRequest,
    DocumentRecord,
    ErrorCategory,
    ResultKind,
    WorkflowResult,
)
from .support import AbstainPolicy, ScoredChunk, score_hit

MAX_ATTEMPTS = 2  # bounded retries: initial attempt + one retry, then abstain
PROMPT_VERSION = "n/a-deterministic"


@dataclass
class WorkflowContext:
    index: ChunkIndex
    registry: dict[str, DocInfo]
    assessor: Assessor = field(default_factory=RuleAssessor)
    policy: AbstainPolicy = field(default_factory=AbstainPolicy.load)
    sink: AuditSink | None = None
    max_attempts: int = MAX_ATTEMPTS
    trace_id_factory: Callable[[], str] = lambda: uuid.uuid4().hex
    retrieval_method: str = "hybrid_rrf"

    @classmethod
    def from_documents(cls, docs: list[DocumentRecord], *, embedder: Embedder | None = None,
                       stopwords: bool = True, subwords: bool = False, **kw: Any) -> WorkflowContext:
        chunks: list[Chunk] = []
        for d in docs:
            chunks.extend(chunk_document(d))
        index = ChunkIndex(chunks, embedder=embedder,
                           analyzer=make_analyzer(stopwords=stopwords, subwords=subwords))
        registry = {d.doc_id: DocInfo(d.doc_id, d.filename, d.version, d.sha256) for d in docs}
        return cls(index=index, registry=registry, **kw)


class State(TypedDict, total=False):
    raw: Any
    request: ClaimRequest
    trace_id: str
    t0: float
    path: list[str]
    flags: list[str]
    notices: list[str]
    error_category: ErrorCategory
    query: str
    allowed: list[str]
    hits: list[RetrievedChunk]
    quarantined: list[str]
    scored: list[ScoredChunk]
    assessment: Assessment
    attempt: int
    citation_errors: list[str]
    abstain: tuple[AssessmentStatus, str, tuple[str, ...]]
    reject_reason: str
    priority: str
    result: WorkflowResult


def _step(state: State, name: str) -> list[str]:
    return [*state.get("path", []), name]


def build_graph(ctx: WorkflowContext):
    def validate_input(s: State) -> State:
        out: State = {"path": _step(s, "validate_input"), "flags": [], "notices": [],
                      "attempt": 0, "quarantined": []}
        try:
            req = ClaimRequest.model_validate(s["raw"])
        except ValidationError as exc:  # report field + error type only, never echo the input
            where = sorted({".".join(map(str, e["loc"])) or "request" for e in exc.errors()})
            out["reject_reason"] = "invalid request: " + ", ".join(where)
            out["error_category"] = ErrorCategory.VALIDATION
            return out
        unknown = [d for d in req.doc_ids if d not in ctx.registry]
        if unknown:
            out["reject_reason"] = "unknown document id in scope"
            out["error_category"] = ErrorCategory.VALIDATION
            return out
        out["request"] = req
        out["allowed"] = list(req.doc_ids)
        return out

    def screen_query(s: State) -> State:
        req = s["request"]
        flags = [f.kind for f in screen_text(req.query)]
        out: State = {"path": _step(s, "screen_query"), "query": strip_hidden(req.query)}
        if flags:
            out["flags"] = [*s["flags"], *(f"query:{f}" for f in flags)]
            out["abstain"] = (AssessmentStatus.HUMAN_REVIEW_REQUIRED,
                              "request contains instruction-like or obfuscated content "
                              f"({', '.join(sorted(set(flags)))}); no retrieval performed",
                              ())
            out["error_category"] = ErrorCategory.GUARDRAIL
        return out

    def retrieve(s: State) -> State:
        cfg = RetrievalConfig(method=ctx.retrieval_method, top_k=s["request"].top_k)
        res = ctx.index.search(s["query"], cfg, doc_ids=set(s["allowed"]))
        notices = list(s["notices"]) + ([res.notice] if res.notice else [])
        return {"path": _step(s, "retrieve"), "hits": list(res.hits), "notices": notices}

    def enforce_scope(s: State) -> State:
        allowed = set(s["allowed"])
        kept = [h for h in s["hits"] if h.chunk.doc_id in allowed]
        out: State = {"path": _step(s, "enforce_scope"), "hits": kept}
        if len(kept) != len(s["hits"]):  # should be impossible; fail closed if it ever happens
            out["flags"] = [*s["flags"], "scope_violation"]
            out["error_category"] = ErrorCategory.GUARDRAIL
            out["abstain"] = (AssessmentStatus.HUMAN_REVIEW_REQUIRED,
                              "retrieval returned evidence outside the permitted document scope; "
                              "results discarded", ())
        return out

    def screen_evidence(s: State) -> State:
        flags = list(s["flags"])
        quarantined = []
        for h in s["hits"]:
            found = screen_text(h.chunk.text)
            if found:
                quarantined.append(h.chunk.chunk_id)
                flags.extend(f"evidence:{f.kind}" for f in found)
        return {"path": _step(s, "screen_evidence"), "flags": flags, "quarantined": quarantined}

    def score_evidence(s: State) -> State:
        scored = [score_hit(s["query"], h, ctx.index, ctx.policy) for h in s["hits"]]
        out: State = {"path": _step(s, "score_evidence")}
        quarantined = set(s["quarantined"])
        if any(x.supported and x.chunk.chunk_id in quarantined for x in scored):
            out["error_category"] = ErrorCategory.GUARDRAIL
            out["abstain"] = (AssessmentStatus.HUMAN_REVIEW_REQUIRED,
                              "supporting evidence contained instruction-like content and was "
                              "quarantined", ())
        usable = tuple(x for x in scored if x.chunk.chunk_id not in quarantined)
        out["scored"] = list(usable)
        if "abstain" not in out and not any(x.supported for x in usable):
            out["abstain"] = (AssessmentStatus.INSUFFICIENT_EVIDENCE,
                              "no retrieved clause is sufficiently related to the request",
                              ("the loss or event, its cause, and the policy section it relates to",))
        return out

    def assess(s: State) -> State:
        inp = AssessmentInput(s["query"], tuple(s["scored"]))
        attempt = s["attempt"]
        try:
            a = ctx.assessor.assess(inp, attempt)
            return {"path": _step(s, "assess"), "assessment": a, "attempt": attempt + 1}
        except Exception as exc:  # noqa: BLE001  - a faulty assessor must not crash the workflow
            return {"path": _step(s, "assess"), "attempt": attempt + 1,
                    "citation_errors": [f"assessor_exception:{type(exc).__name__}"],
                    "assessment": None}  # type: ignore[typeddict-item]

    def validate_cit(s: State) -> State:
        a = s.get("assessment")
        if a is None:
            errs = s.get("citation_errors", ["no_assessment"])
        else:
            retrieved = {c.chunk_id: c for x in s["scored"] for c in (x.chunk, *x.continuation)}
            errs = [str(e) for e in validate_citations(a, retrieved, s["allowed"], ctx.registry)]
        out: State = {"path": _step(s, "validate_citations"), "citation_errors": errs}
        if errs and s["attempt"] >= ctx.max_attempts:
            out["flags"] = [*s["flags"], "citation_validation_failed"]
            out["error_category"] = ErrorCategory.GUARDRAIL
            out["abstain"] = (AssessmentStatus.HUMAN_REVIEW_REQUIRED,
                              f"assessment failed citation validation after {s['attempt']} "
                              f"attempt(s): {', '.join(sorted({e.split(':')[0] for e in errs}))}", ())
        return out

    def abstain(s: State) -> State:
        status, reason, missing = s["abstain"]
        kw: dict[str, Any] = {"missing_information": missing} if missing else {}
        if status == AssessmentStatus.HUMAN_REVIEW_REQUIRED:
            kw["escalation_reason"] = reason
        a = Assessment(status=status, summary="No automated assessment was produced.",
                       uncertainty=reason, model_version=f"{ctx.assessor.name}-{ctx.assessor.version}",
                       prompt_version=PROMPT_VERSION, **kw)
        return {"path": _step(s, "abstain"), "assessment": a}

    def reject(s: State) -> State:
        return {"path": _step(s, "reject")}

    def human_review_gate(s: State) -> State:
        a = s["assessment"]
        mandatory = (a.status != AssessmentStatus.POTENTIALLY_COVERED
                     and a.status != AssessmentStatus.POTENTIALLY_EXCLUDED) or bool(s["flags"])
        return {"path": _step(s, "human_review_gate"),
                "priority": "mandatory" if mandatory else "standard"}

    def audit(s: State) -> State:
        path = _step(s, "audit")
        rejected = "reject_reason" in s
        a = s.get("assessment")
        req = s.get("request")
        raw = s.get("raw")
        raw_q = raw.get("query") if isinstance(raw, Mapping) else None
        import hashlib

        qhash = hashlib.sha256(raw_q.encode()).hexdigest() if isinstance(raw_q, str) else None
        scored = s.get("scored", [])
        allowed = s.get("allowed", [])
        rec = AuditRecord(
            trace_id=s["trace_id"],
            doc_ids=tuple(allowed),
            doc_sha256s=tuple(ctx.registry[d].sha256 for d in allowed),
            query_sha256=qhash,
            retrieval=None if req is None or "hits" not in s else RetrievalConfigRecordFactory(ctx, req),
            retrieved_chunk_ids=tuple(x.chunk.chunk_id for x in scored),
            model_version=f"{ctx.assessor.name}-{ctx.assessor.version}",
            prompt_version=PROMPT_VERSION,
            outcome=a.status if a else None,
            escalation_reason=a.escalation_reason if a else None,
            latency_ms=(time.perf_counter() - s["t0"]) * 1000,
            error_category=s.get("error_category", ErrorCategory.NONE),
            node_path=tuple(path), guardrail_flags=tuple(sorted(set(s.get("flags", [])))))
        if rejected:
            kind = ResultKind.REJECTED
        elif a is not None and a.status in (AssessmentStatus.POTENTIALLY_COVERED,
                                            AssessmentStatus.POTENTIALLY_EXCLUDED):
            kind = ResultKind.ASSESSED
        else:
            kind = ResultKind.ABSTAINED
        result = WorkflowResult(
            trace_id=s["trace_id"], kind=kind, assessment=None if rejected else a,
            reject_reason=s.get("reject_reason"), review_priority=s.get("priority", "mandatory"),
            retrieved=tuple(x.chunk.to_evidence(score=x.hit.score) for x in scored),
            quarantined_chunk_ids=tuple(s.get("quarantined", [])),
            notices=tuple(s.get("notices", [])), audit=rec)
        if ctx.sink is not None:
            ctx.sink.write(audit_event(rec))
        return {"path": path, "result": result}

    # ---- routing ----
    def after_validate(s: State) -> str:
        return "reject" if "reject_reason" in s else "screen_query"

    def after_screen_query(s: State) -> str:
        return "abstain" if "abstain" in s else "retrieve"

    def after_scope(s: State) -> str:
        return "abstain" if "abstain" in s else "screen_evidence"

    def after_score(s: State) -> str:
        return "abstain" if "abstain" in s else "assess"

    def after_cit(s: State) -> str:
        if not s["citation_errors"]:
            return "human_review_gate"
        return "abstain" if "abstain" in s else "assess"

    g = StateGraph(State)
    for name, fn in (("validate_input", validate_input), ("screen_query", screen_query),
                     ("retrieve", retrieve), ("enforce_scope", enforce_scope),
                     ("screen_evidence", screen_evidence), ("score_evidence", score_evidence),
                     ("assess", assess), ("validate_citations", validate_cit),
                     ("abstain", abstain), ("reject", reject),
                     ("human_review_gate", human_review_gate), ("audit", audit)):
        g.add_node(name, fn)
    g.add_edge(START, "validate_input")
    g.add_conditional_edges("validate_input", after_validate, ["reject", "screen_query"])
    g.add_conditional_edges("screen_query", after_screen_query, ["abstain", "retrieve"])
    g.add_edge("retrieve", "enforce_scope")
    g.add_conditional_edges("enforce_scope", after_scope, ["abstain", "screen_evidence"])
    g.add_edge("screen_evidence", "score_evidence")
    g.add_conditional_edges("score_evidence", after_score, ["abstain", "assess"])
    g.add_edge("assess", "validate_citations")
    g.add_conditional_edges("validate_citations", after_cit,
                            ["human_review_gate", "assess", "abstain"])
    g.add_edge("abstain", "human_review_gate")
    g.add_edge("human_review_gate", "audit")
    g.add_edge("reject", "audit")
    g.add_edge("audit", END)
    return g.compile()


def RetrievalConfigRecordFactory(ctx: WorkflowContext, req: ClaimRequest):
    from .schemas import RetrievalConfigRecord

    cfg = RetrievalConfig(method=ctx.retrieval_method, top_k=req.top_k)
    return RetrievalConfigRecord(
        method=cfg.method, top_k=cfg.top_k,
        params={"rrf_k": cfg.rrf_k, "depth": cfg.depth, "config_fp": cfg.fingerprint(),
                "corpus_fp": ctx.index.corpus_fp, "abstain_policy": ctx.policy.version,
                "tau_lex": ctx.policy.tau_lex,
                "semantic": "on" if ctx.index.semantic_enabled else "off"})


class Workflow:
    def __init__(self, ctx: WorkflowContext) -> None:
        self.ctx = ctx
        self.graph = build_graph(ctx)

    def run(self, raw: Any) -> WorkflowResult:
        state = self.graph.invoke({"raw": raw, "trace_id": self.ctx.trace_id_factory(),
                                   "t0": time.perf_counter(), "path": []})
        return state["result"]

    def mermaid(self) -> str:
        return self.graph.get_graph().draw_mermaid()