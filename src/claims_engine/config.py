"""Central, reproducible configuration. Values can be overridden via environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


@dataclass(frozen=True)
class IngestionLimits:
    max_file_bytes: int = 10 * 1024 * 1024  # 10 MiB
    max_pages: int = 200
    min_page_chars: int = 20  # below this a page is treated as empty
    min_ok_page_ratio: float = 0.5  # fewer usable pages than this -> extraction failure

    @classmethod
    def from_env(cls) -> IngestionLimits:
        return cls(
            max_file_bytes=_int("CLAIMS_MAX_FILE_BYTES", cls.max_file_bytes),
            max_pages=_int("CLAIMS_MAX_PAGES", cls.max_pages),
        )


@dataclass(frozen=True)
class BM25Params:
    k1: float = 1.5
    b: float = 0.75


# Optional semantic model. Never downloaded automatically: see embeddings.py / fetch_model.py.
# Multilingual (50+ languages incl. EN/FR/DE), 384-dim, Apache-2.0, ~449 MB safetensors.
# Revision is a pinned Hugging Face commit (looked up via the HF API on 2026-10-27).
EMBEDDING_MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EMBEDDING_LOCAL_DIR = PROJECT_ROOT / "models" / "paraphrase-multilingual-MiniLM-L12-v2"
MODEL_MANIFEST = "MODEL_MANIFEST.json"
