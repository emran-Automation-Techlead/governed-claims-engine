"""Shared test helpers (importable as `helpers`)."""
import re

import numpy as np

from claims_engine.citations import DocInfo
from claims_engine.retrieval import ChunkIndex
from claims_engine.support import AbstainPolicy
from claims_engine.workflow import Workflow, WorkflowContext

POLICY = AbstainPolicy(version="test", tau_lex=0.5, tau_sem=None)


class FakeEmbedder:
    """Letter-frequency 'embedding': deterministic, offline stand-in for the real model."""

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


def make_wf(everything, *, only=None, embedder=None, policy=POLICY, **kw) -> tuple[Workflow, dict]:
    docs = [d for n, d in everything.items() if only is None or n in only]
    ctx = WorkflowContext.from_documents(docs, embedder=embedder, stopwords=False, policy=policy,
                                         trace_id_factory=lambda: "trace-test", **kw)
    return Workflow(ctx), {d.filename: d.doc_id for d in docs}


def ask(wf, ids, filename, query, **extra):
    return wf.run({"query": query, "doc_ids": [ids[filename]], **extra})


def registry_of(docs) -> dict[str, DocInfo]:
    return {d.doc_id: DocInfo(d.doc_id, d.filename, d.version, d.sha256) for d in docs}


def index_of(chunks, **kw) -> ChunkIndex:
    return ChunkIndex(chunks, **kw)