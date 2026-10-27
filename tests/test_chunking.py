import re

import pytest

from claims_engine.chunking import chunk_document
from claims_engine.ingestion import ingest_pdf_bytes, ingest_pdf_path
from conftest import make_pdf


def chunks_of(policy_path):
    doc = ingest_pdf_path(policy_path)
    return doc, chunk_document(doc)


def by_clause(chunks, clause):
    return [c for c in chunks if c.clause_id == clause]


def test_home_policy_has_one_chunk_per_clause(policies):
    doc, cs = chunks_of(policies["home"])
    ids = [c.clause_id for c in cs]
    assert ids == ["1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "3.1", "3.2", "3.3",
                   "4.1", "4.2", "4.3", "4.4", "5.1", "5.2", "5.3", "5.4"]
    assert len(cs) == 17


def test_page_numbers_match_source_pages(policies):
    doc, cs = chunks_of(policies["home"])
    expect = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
    for c in cs:
        assert c.page_number == expect[c.clause_id.split(".")[0]]


def test_every_chunk_text_is_found_on_its_own_page(policies):
    for key in ("home", "travel"):
        doc, cs = chunks_of(policies[key])
        for c in cs:
            page_text = " ".join(doc.pages[c.page_number - 1].text.split())
            assert " ".join(c.text.split()) in page_text, c.chunk_id


def test_running_headers_and_footers_removed(policies):
    _, cs = chunks_of(policies["home"])
    for c in cs:
        assert "SYNTHETIC DOCUMENT" not in c.text
        assert "Fictional Home Insurance Policy" not in c.text
        assert not re.search(r"Page \d+ of \d+", c.text)


def test_provenance_fields(policies):
    doc, cs = chunks_of(policies["travel"])
    for c in cs:
        assert (c.doc_id, c.doc_sha256, c.doc_version, c.filename) == (
            doc.doc_id, doc.sha256, doc.version, doc.filename)
    assert len({c.chunk_id for c in cs}) == len(cs)
    assert cs[0].chunk_id == f"{doc.doc_id}:p1:1.1"


def test_version_propagates():
    doc = ingest_pdf_bytes(make_pdf(["1. A\n1.1 Cover. We cover fire damage fully."] * 3),
                           "v.pdf", version="2025-03")
    assert all(c.doc_version == "2025-03" for c in chunk_document(doc))


def test_section_title_gives_context_and_is_indexed(policies):
    _, cs = chunks_of(policies["home"])
    c = by_clause(cs, "4.3")[0]
    assert c.section_id == "4" and c.section_title == "Exclusions"
    assert c.index_text.startswith("Exclusions. 4.3 Unoccupied Property")
    assert "Exclusions" not in c.text.split(".")[0]  # context lives in index_text, text is verbatim


def test_conditions_and_exceptions_stay_inside_their_clause(policies):
    _, home = chunks_of(policies["home"])
    flood = by_clause(home, "3.3")[0].text
    assert "only if the optional" in flood and "Flood Extension" in flood
    unocc = by_clause(home, "4.3")[0].text
    assert "60" in unocc and "suspended" in unocc
    _, travel = chunks_of(policies["travel"])
    pre = by_clause(travel, "2.3")[0].text
    assert "excluded unless declared" in pre and "in writing before the trip" in pre


def test_numbers_at_line_start_are_not_mistaken_for_clauses(policies):
    _, cs = chunks_of(policies["travel"])
    delay = by_clause(cs, "3.2")[0].text
    assert "8 hours and EUR 25" in delay and "up to EUR 200" in delay
    assert [c.clause_id for c in cs if c.page_number == 3] == ["3.1", "3.2", "3.3"]


def test_neighbour_links_form_a_chain(policies):
    _, cs = chunks_of(policies["home"])
    assert cs[0].prev_chunk_id is None and cs[-1].next_chunk_id is None
    for a, b in zip(cs, cs[1:]):
        assert a.next_chunk_id == b.chunk_id and b.prev_chunk_id == a.chunk_id


def test_chunking_is_deterministic(policies):
    doc = ingest_pdf_path(policies["home"])
    assert chunk_document(doc) == chunk_document(doc)


def test_french_and_german_policies_chunk_by_clause(all_policies):
    for name, expected_pages in (("synthetic_home_policy_fr.pdf", 3),
                                 ("synthetic_home_policy_de.pdf", 3)):
        doc = ingest_pdf_path(all_policies[name])
        cs = chunk_document(doc)
        assert doc.page_count == expected_pages
        assert [c.clause_id for c in cs] == ["1.1", "1.2", "1.3", "2.1", "2.2", "2.3",
                                             "3.1", "3.2", "3.3"]
        assert all("SYNTHETIC DOCUMENT" not in c.text for c in cs)
    de = chunk_document(ingest_pdf_path(all_policies["synthetic_home_policy_de.pdf"]))
    assert "Verschleiß" in by_clause(de, "3.1")[0].text  # accents survive extraction
    fr = chunk_document(ingest_pdf_path(all_policies["synthetic_home_policy_fr.pdf"]))
    assert fr[1].text.startswith("1.2 « Dégât des eaux »")


def test_clause_running_over_a_page_break_becomes_two_chunks_with_exact_pages():
    pages = [
        "1. Cover\n1.1 Fire. We cover fire damage to the insured home if the\n"
        "home is maintained properly and",
        "the alarm was active at the time of the loss. Unless stated otherwise.\n"
        "1.2 Theft. We cover theft with forced entry.",
        "2. Other\n2.1 Limit. The maximum payable is EUR 5,000 per claim.",
    ]
    cs = chunk_document(ingest_pdf_bytes(make_pdf(pages), "x.pdf"))
    f = by_clause(cs, "1.1")
    assert [(c.page_number, c.continues_previous) for c in f] == [(1, False), (2, True)]
    assert "alarm was active" in f[1].text and "alarm" not in f[0].text
    assert "Unless stated otherwise" in f[1].text  # the exception survives, on the right page
    assert f[1].prev_chunk_id == f[0].chunk_id
    assert by_clause(cs, "1.2")[0].page_number == 2
    assert by_clause(cs, "2.1")[0].page_number == 3


def test_long_clause_is_split_on_sentences_with_one_sentence_overlap():
    sentences = [f"Condition number {i} applies to the insured." for i in range(1, 9)]
    pages = ["1. Rules\n1.1 Long clause. " + "\n".join(sentences),
             "2. Filler\n2.1 Filler. Page with enough text to be counted as usable here.",
             "3. Filler\n3.1 Filler. Another page with enough text to be counted as usable."]
    cs = [c for c in chunk_document(ingest_pdf_bytes(make_pdf(pages), "x.pdf"), max_chars=150)
          if c.clause_id == "1.1"]
    assert len(cs) >= 3
    assert cs[0].chunk_id.endswith(":1.1") and cs[1].chunk_id.endswith(":1.1:s1")
    assert all(len(c.text) <= 150 + 60 for c in cs)
    for a, b in zip(cs, cs[1:]):  # last sentence of a chunk reopens the next one
        assert a.text.split(". ")[-1].rstrip(".") in b.text
    joined = " ".join(c.text for c in cs)
    for s in sentences:
        assert s.rstrip(".") in joined  # nothing lost


def test_bare_section_heading_is_context_only_not_a_chunk():
    pages = ["1. Empty Section\n2. Real Section\n2.1 Clause. Some real clause text here.",
             "x" * 30, "y" * 30]
    cs = chunk_document(ingest_pdf_bytes(make_pdf(pages), "x.pdf"))
    assert not any(c.clause_id is None and c.text.startswith("1. Empty") for c in cs)
    assert by_clause(cs, "2.1")[0].section_title == "Real Section"


def test_text_before_first_clause_is_kept_as_preamble():
    pages = ["This policy is issued by a fictional insurer for testing only.\n1. A\n1.1 Cover. Fire.",
             "z" * 30, "w" * 30]
    cs = chunk_document(ingest_pdf_bytes(make_pdf(pages), "x.pdf"))
    assert cs[0].clause_id is None and cs[0].chunk_id.endswith(":p1:pre")
    assert "fictional insurer" in cs[0].text


def test_empty_pages_are_skipped_without_shifting_page_numbers():
    pages = ["1. A\n1.1 Cover. We cover fire damage fully.", "",
             "2. B\n2.1 Limit. We pay up to EUR 100 in total."]
    doc = ingest_pdf_bytes(make_pdf(pages), "x.pdf")
    cs = chunk_document(doc)
    assert [(c.clause_id, c.page_number) for c in cs] == [("1.1", 1), ("2.1", 3)]


@pytest.mark.parametrize("bad", [0, -5])
def test_chunk_schema_rejects_invalid_page(bad, policies):
    from claims_engine.schemas import Chunk

    _, cs = chunks_of(policies["home"])
    with pytest.raises(ValueError):
        Chunk.model_validate({**cs[0].model_dump(), "page_number": bad})

def test_chunk_to_evidence_keeps_provenance(policies):
    doc, cs = chunks_of(policies["home"])
    ev = by_clause(cs, "3.2")[0].to_evidence(score=1.5)
    assert (ev.doc_id, ev.doc_sha256, ev.page_number, ev.clause_id) == (
        doc.doc_id, doc.sha256, 3, "3.2")
    assert ev.quote.startswith("3.2 Gradual Leakage") and ev.score == 1.5