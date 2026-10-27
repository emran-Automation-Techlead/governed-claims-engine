r"""Explicit, opt-in download of the pinned embedding model into ./models (project-local).

Run deliberately:  .venv\Scripts\python -m claims_engine.fetch_model
Only the files needed for sentence-transformers inference are fetched (no onnx/openvino/tf copies).
Writes MODEL_MANIFEST.json (repo, pinned revision, per-file SHA-256) that embeddings.py verifies.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request

from huggingface_hub import snapshot_download

from .config import (
    EMBEDDING_LOCAL_DIR,
    EMBEDDING_MODEL_ID,
    EMBEDDING_MODEL_REVISION,
    MODEL_MANIFEST,
)

FILES = [
    "1_Pooling/config.json", "config.json", "config_sentence_transformers.json",
    "modules.json", "sentence_bert_config.json", "special_tokens_map.json",
    "tokenizer_config.json", "tokenizer.json", "sentencepiece.bpe.model", "model.safetensors",
]


def _sha(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    EMBEDDING_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_download(EMBEDDING_MODEL_ID, revision=EMBEDDING_MODEL_REVISION,
                      allow_patterns=FILES, local_dir=str(EMBEDDING_LOCAL_DIR))
    api = f"https://huggingface.co/api/models/{EMBEDDING_MODEL_ID}/revision/{EMBEDDING_MODEL_REVISION}"
    if not api.startswith("https://huggingface.co/"):  # fixed constant today; guard against file:/custom schemes
        raise SystemExit("refusing non-https model metadata URL")
    meta = json.load(urllib.request.urlopen(api + "?blobs=true"))  # noqa: S310 - scheme checked above
    remote = {s["rfilename"]: s for s in meta["siblings"]}
    files = {}
    for name in FILES:
        digest = _sha(EMBEDDING_LOCAL_DIR / name)
        lfs = (remote.get(name) or {}).get("lfs")
        if lfs and lfs.get("sha256") != digest:
            raise SystemExit(f"CHECKSUM MISMATCH for {name}: local {digest} != hub {lfs['sha256']}")
        files[name] = digest
    manifest = {"repo_id": EMBEDDING_MODEL_ID, "revision": EMBEDDING_MODEL_REVISION,
                "resolved_sha": meta.get("sha"), "files": files}
    (EMBEDDING_LOCAL_DIR / MODEL_MANIFEST).write_text(json.dumps(manifest, indent=2), "utf-8")
    print("downloaded and verified:", EMBEDDING_LOCAL_DIR)


if __name__ == "__main__":
    main()