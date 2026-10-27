"""OPTIONAL semantic embeddings. The application works without this module's dependencies.

Safety properties:
* `sentence-transformers` is imported lazily, only inside `load_embedder`.
* Offline by construction: HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE are set and the model is loaded
  with `local_files_only=True`. This code NEVER downloads. Fetching is a separate, explicit
  command: `python -m claims_engine.fetch_model`.
* The local copy must carry a MODEL_MANIFEST.json naming the pinned repo + revision, and every
  listed file's SHA-256 must match, otherwise loading is refused.
* Any failure raises EmbeddingUnavailable with a human-readable reason so callers fall back to
  lexical-only retrieval and can tell the user that semantic retrieval is disabled.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from collections.abc import Sequence
from pathlib import Path

from .config import (
    EMBEDDING_LOCAL_DIR,
    EMBEDDING_MODEL_ID,
    EMBEDDING_MODEL_REVISION,
    MODEL_MANIFEST,
)


class EmbeddingUnavailable(RuntimeError):
    pass


def is_available() -> bool:
    """True if the optional package is importable (does not import it, no network)."""
    return importlib.util.find_spec("sentence_transformers") is not None


class Embedder:
    def __init__(self, model, model_id: str, revision: str) -> None:
        self._model = model
        self.model_id = model_id
        self.revision = revision

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        vecs = self._model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return [list(map(float, v)) for v in vecs]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_local_model(model_dir: Path, *, revision: str = EMBEDDING_MODEL_REVISION,
                       repo_id: str = EMBEDDING_MODEL_ID) -> None:
    """Raise EmbeddingUnavailable unless model_dir is the pinned revision with intact files."""
    manifest_path = model_dir / MODEL_MANIFEST
    if not manifest_path.is_file():
        raise EmbeddingUnavailable(
            f"no local model at {model_dir}; semantic retrieval is disabled "
            "(run `python -m claims_engine.fetch_model` to fetch it deliberately)")
    try:
        manifest = json.loads(manifest_path.read_text("utf-8"))
    except (OSError, ValueError) as exc:
        raise EmbeddingUnavailable(f"unreadable model manifest ({type(exc).__name__})") from exc
    if manifest.get("repo_id") != repo_id or manifest.get("revision") != revision:
        raise EmbeddingUnavailable("local model is not the pinned repo/revision; refusing to load")
    for name, digest in manifest.get("files", {}).items():
        f = model_dir / name
        if not f.is_file() or _sha256(f) != digest:
            raise EmbeddingUnavailable(f"model file failed integrity check: {name}")


def load_embedder(model_dir: str | Path = EMBEDDING_LOCAL_DIR) -> Embedder:
    if not is_available():
        raise EmbeddingUnavailable(
            "sentence-transformers is not installed; semantic retrieval is disabled (lexical-only)")
    model_dir = Path(model_dir)
    verify_local_model(model_dir)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(str(model_dir), device="cpu", local_files_only=True)
    except Exception as exc:
        raise EmbeddingUnavailable(
            f"model could not be loaded ({type(exc).__name__}); semantic retrieval is disabled"
        ) from exc
    return Embedder(model, EMBEDDING_MODEL_ID, EMBEDDING_MODEL_REVISION)