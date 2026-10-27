from pathlib import Path

import fitz
import pytest

from claims_engine.ingestion import ingest_pdf_path
from claims_engine.synthetic import generate, generate_all, generate_everything


@pytest.fixture(scope="session")
def all_policies(tmp_path_factory) -> dict[str, Path]:
    out = tmp_path_factory.mktemp("all_policies")
    return {p.name: p for p in generate_all(out)}


@pytest.fixture(scope="session")
def policies(tmp_path_factory) -> dict[str, Path]:
    out = tmp_path_factory.mktemp("policies")
    home, travel = generate(out)
    return {"home": home, "travel": travel}


def make_pdf(page_texts: list[str], *, encrypt: bool = False) -> bytes:
    """Build a PDF in memory. An empty string yields a genuinely blank page."""
    doc = fitz.open()
    for t in page_texts:
        page = doc.new_page()
        if t:
            page.insert_text((72, 72), t)
    if encrypt:
        data = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="u", owner_pw="o")
    else:
        data = doc.tobytes()
    doc.close()
    return data


LONG = "This page contains enough extractable text to count as usable."


@pytest.fixture(scope="session")
def everything(tmp_path_factory):
    """All 8 synthetic documents (4 original, 3 held-out, 1 adversarial) as DocumentRecords."""
    root = tmp_path_factory.mktemp("everything")
    docs = [ingest_pdf_path(p) for p in generate_everything(root)]
    return {d.filename: d for d in docs}