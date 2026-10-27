import hashlib
import json
import os
import sys

import pytest

from claims_engine import embeddings
from claims_engine.config import (
    EMBEDDING_LOCAL_DIR,
    EMBEDDING_MODEL_ID,
    EMBEDDING_MODEL_REVISION,
    MODEL_MANIFEST,
)
from claims_engine.embeddings import EmbeddingUnavailable, load_embedder, verify_local_model

MODEL_PRESENT = embeddings.is_available() and (EMBEDDING_LOCAL_DIR / MODEL_MANIFEST).is_file()
needs_model = pytest.mark.skipif(not MODEL_PRESENT, reason="optional model/package not installed")


def test_is_available_returns_bool_without_importing_heavy_package():
    before = "sentence_transformers" in sys.modules
    assert isinstance(embeddings.is_available(), bool)
    assert ("sentence_transformers" in sys.modules) == before


def test_missing_package_falls_back_cleanly(monkeypatch):
    monkeypatch.setattr(embeddings, "is_available", lambda: False)
    with pytest.raises(EmbeddingUnavailable, match="lexical-only"):
        load_embedder()


def test_missing_local_model_never_downloads(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(embeddings, "is_available", lambda: True)
    with pytest.raises(EmbeddingUnavailable, match="semantic retrieval is disabled"):
        load_embedder(tmp_path / "no-such-model")
    assert calls == []


def _fake_model_dir(tmp_path, **manifest_overrides):
    (tmp_path / "weights.bin").write_bytes(b"abc")
    manifest = {"repo_id": EMBEDDING_MODEL_ID, "revision": EMBEDDING_MODEL_REVISION,
                "files": {"weights.bin": hashlib.sha256(b"abc").hexdigest()}}
    manifest.update(manifest_overrides)
    (tmp_path / MODEL_MANIFEST).write_text(json.dumps(manifest), "utf-8")
    return tmp_path


def test_verify_accepts_intact_pinned_model(tmp_path):
    verify_local_model(_fake_model_dir(tmp_path))


def test_verify_rejects_wrong_revision(tmp_path):
    with pytest.raises(EmbeddingUnavailable, match="pinned"):
        verify_local_model(_fake_model_dir(tmp_path, revision="0" * 40))


def test_verify_rejects_wrong_repo(tmp_path):
    with pytest.raises(EmbeddingUnavailable, match="pinned"):
        verify_local_model(_fake_model_dir(tmp_path, repo_id="someone/else"))


def test_verify_rejects_tampered_file(tmp_path):
    d = _fake_model_dir(tmp_path)
    (d / "weights.bin").write_bytes(b"tampered")
    with pytest.raises(EmbeddingUnavailable, match="integrity"):
        verify_local_model(d)


def test_verify_rejects_missing_file_and_corrupt_manifest(tmp_path):
    d = _fake_model_dir(tmp_path)
    (d / "weights.bin").unlink()
    with pytest.raises(EmbeddingUnavailable, match="integrity"):
        verify_local_model(d)
    (d / MODEL_MANIFEST).write_text("{not json", "utf-8")
    with pytest.raises(EmbeddingUnavailable, match="manifest"):
        verify_local_model(d)


@pytest.mark.semantic
@needs_model
def test_real_model_loads_offline_and_is_deterministic():
    emb = load_embedder()
    assert os.environ["HF_HUB_OFFLINE"] == "1" and os.environ["TRANSFORMERS_OFFLINE"] == "1"
    assert emb.revision == EMBEDDING_MODEL_REVISION
    a = emb.encode(["burst pipe", "dégât des eaux"])
    b = emb.encode(["burst pipe", "dégât des eaux"])
    assert a == b and len(a[0]) == 384
    assert sum(x * x for x in a[0]) == pytest.approx(1.0, abs=1e-4)  # L2-normalised


@pytest.mark.semantic
@needs_model
def test_real_model_is_multilingual_en_fr_de():
    emb = load_embedder()
    q, water_fr, theft_fr, water_de = emb.encode([
        "pipe burst water damage", "rupture soudaine de canalisation et dégât des eaux",
        "vol avec effraction constatée", "plötzlicher Rohrbruch Leitungswasserschaden"])

    def cos(x, y):
        return sum(a * b for a, b in zip(x, y))

    assert cos(q, water_fr) > cos(q, theft_fr)
    assert cos(q, water_de) > cos(q, theft_fr)


@pytest.mark.semantic
@needs_model
def test_real_model_hybrid_index_end_to_end(all_policies):
    from claims_engine.chunking import chunk_document
    from claims_engine.ingestion import ingest_pdf_path
    from claims_engine.retrieval import ChunkIndex, RetrievalConfig

    chunks, ids = [], {}
    for name, path in sorted(all_policies.items()):
        d = ingest_pdf_path(path)
        ids[name] = d.doc_id
        chunks += chunk_document(d)
    idx = ChunkIndex(chunks, embedder=load_embedder())
    res = idx.search("my kitchen pipe suddenly burst and flooded the floor",
                     RetrievalConfig(method="hybrid_rrf", top_k=3),
                     doc_ids={ids["synthetic_home_policy.pdf"]})
    assert not res.degraded and res.embedding_revision == EMBEDDING_MODEL_REVISION
    assert "3.1" in [h.chunk.clause_id for h in res.hits]