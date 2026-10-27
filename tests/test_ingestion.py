import hashlib

import pytest

from claims_engine.config import IngestionLimits
from claims_engine.ingestion import IngestionError, ingest_pdf_bytes, ingest_pdf_path
from claims_engine.schemas import PageStatus
from conftest import LONG, make_pdf


def page_of(doc, needle):
    return [p.page_number for p in doc.pages if needle in p.text]


def test_valid_home_policy(policies):
    doc = ingest_pdf_path(policies["home"])
    assert doc.page_count == 5 and len(doc.pages) == 5
    assert all(p.status == PageStatus.OK for p in doc.pages)
    assert doc.filename == "synthetic_home_policy.pdf"
    assert doc.warnings == ()
    assert "SYNTHETIC DOCUMENT" in doc.pages[0].text


def test_valid_travel_policy(policies):
    doc = ingest_pdf_path(policies["travel"])
    assert doc.page_count == 4


def test_page_references_are_correct(policies):
    home = ingest_pdf_path(policies["home"])
    assert page_of(home, "3.1 Burst Pipes") == [3]
    assert page_of(home, "4.3 Unoccupied Property") == [4]
    assert page_of(home, "5.3 Excess") == [5]
    travel = ingest_pdf_path(policies["travel"])
    assert page_of(travel, "2.2 Repatriation") == [2]
    assert page_of(travel, "4.2 Unattended Items") == [4]


def test_hash_matches_file_bytes(policies):
    raw = policies["home"].read_bytes()
    doc = ingest_pdf_bytes(raw, "x.pdf")
    assert doc.sha256 == hashlib.sha256(raw).hexdigest()
    assert doc.doc_id == f"doc-{doc.sha256[:12]}"
    assert doc.size_bytes == len(raw)


def test_hash_is_stable_and_differs_between_documents(policies):
    a1 = ingest_pdf_path(policies["home"])
    a2 = ingest_pdf_path(policies["home"])
    b = ingest_pdf_path(policies["travel"])
    assert a1.sha256 == a2.sha256 != b.sha256


def test_version_recorded(policies):
    assert ingest_pdf_path(policies["home"], version="2025-01").version == "2025-01"


def test_generator_is_reproducible(tmp_path):
    from claims_engine.synthetic import generate

    first = [p.read_bytes() for p in generate(tmp_path / "a")]
    second = [p.read_bytes() for p in generate(tmp_path / "b")]
    assert first == second


def test_empty_page_is_flagged_not_dropped():
    doc = ingest_pdf_bytes(make_pdf([LONG, "", LONG]), "gap.pdf")
    assert [p.status for p in doc.pages] == [PageStatus.OK, PageStatus.EMPTY, PageStatus.OK]
    assert doc.pages[1].page_number == 2  # numbering preserved
    assert doc.warnings and "[2]" in doc.warnings[0]


def test_all_pages_blank_rejected():
    with pytest.raises(IngestionError) as e:
        ingest_pdf_bytes(make_pdf(["", ""]), "scan.pdf")
    assert e.value.code == "no_text"


def test_mostly_empty_rejected_as_poor_extraction():
    with pytest.raises(IngestionError) as e:
        ingest_pdf_bytes(make_pdf([LONG, "", "", ""]), "poor.pdf")
    assert e.value.code == "poor_extraction"


@pytest.mark.parametrize(
    "data,name,code",
    [
        (b"", "a.pdf", "empty_file"),
        (b"hello world, not a pdf", "a.pdf", "bad_magic"),
        (b"%PDF-1.7\n garbage garbage", "a.pdf", "malformed_pdf"),
        (make_pdf([LONG]), "a.txt", "bad_extension"),
        (make_pdf([LONG]), "a.pdf.exe", "bad_extension"),
        (b"MZ\x90\x00 executable", "evil.pdf", "bad_magic"),
    ],
)
def test_rejects_invalid_inputs(data, name, code):
    with pytest.raises(IngestionError) as e:
        ingest_pdf_bytes(data, name)
    assert e.value.code == code


def test_truncated_pdf_rejected_or_unusable(policies):
    raw = policies["home"].read_bytes()[:300]
    with pytest.raises(IngestionError):
        ingest_pdf_bytes(raw, "cut.pdf")


def test_encrypted_pdf_rejected():
    with pytest.raises(IngestionError) as e:
        ingest_pdf_bytes(make_pdf([LONG], encrypt=True), "enc.pdf")
    assert e.value.code == "encrypted"


def test_size_limit_bytes_and_path(tmp_path):
    data = make_pdf([LONG])
    small = IngestionLimits(max_file_bytes=len(data) - 1)
    with pytest.raises(IngestionError) as e:
        ingest_pdf_bytes(data, "big.pdf", limits=small)
    assert e.value.code == "too_large"
    p = tmp_path / "big.pdf"
    p.write_bytes(data)
    with pytest.raises(IngestionError) as e:
        ingest_pdf_path(p, limits=small)
    assert e.value.code == "too_large"


def test_page_limit():
    with pytest.raises(IngestionError) as e:
        ingest_pdf_bytes(make_pdf([LONG] * 4), "p.pdf", limits=IngestionLimits(max_pages=3))
    assert e.value.code == "too_many_pages"


def test_directory_components_stripped_from_filename():
    doc = ingest_pdf_bytes(make_pdf([LONG]), "../../etc/passwd.pdf")
    assert doc.filename == "passwd.pdf"


def test_missing_file_reports_unreadable(tmp_path):
    with pytest.raises(IngestionError) as e:
        ingest_pdf_path(tmp_path / "nope.pdf")
    assert e.value.code == "unreadable"


def test_control_characters_removed_and_whitespace_normalised():
    from claims_engine.ingestion import _clean

    assert _clean("a\x00b\x07c  \t d\n\n\n  e  ") == "abc d\ne"
