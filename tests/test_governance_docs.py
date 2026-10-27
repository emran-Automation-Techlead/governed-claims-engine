"""The governance documents must exist, record verification levels and must not claim compliance or certification."""
import re
from pathlib import Path

import pytest

GOV = Path(__file__).resolve().parents[1] / "governance"
FILES = ["README.md", "LEGAL_REFERENCES.md", "AI_SYSTEM_CARD.md", "RISK_ASSESSMENT.md", "THREAT_MODEL.md",
         "GRADIO_SECURITY_REVIEW.md", "DEPENDENCY_REPORT.md", "PILLOW_ADVISORY_REVIEW.md", "AUDIT_SCHEMA.md", "EVALUATION_PROTOCOL.md",
         "OPERATIONAL_RESILIENCE.md", "DATA_PROTECTION.md"]
CLAIMS = re.compile(r"(?i)\b(is|are|fully|now)\s+(gdpr|dora|ai[- ]act|eu)[- ]compliant\b|\bcomplies with (the )?(gdpr|dora|ai act)\b"
                    r"|\b(is|are|has been|have been)\s+(legally\s+)?certified\b|\bcertified (compliant|secure)\b|\bproduction[- ]ready\b(?<!not production-ready)")


@pytest.mark.parametrize("name", FILES)
def test_document_exists_and_is_not_empty(name):
    assert len((GOV / name).read_text("utf-8").strip()) > 500


@pytest.mark.parametrize("name", [f for f in FILES if f != "README.md"])
def test_no_document_claims_compliance_certification_or_production_readiness(name):
    text = (GOV / name).read_text("utf-8")
    for m in CLAIMS.finditer(text):
        window = text[max(0, m.start() - 40): m.end() + 10].lower()
        assert re.search(r"\b(not|no|never|nor|without|n't|neither)\b", window), f"{name}: {m.group(0)!r} near {window!r}"


def test_legal_references_record_sources_dates_levels_and_the_limits_of_verification():
    t = (GOV / "LEGAL_REFERENCES.md").read_text("utf-8")
    assert "2026-10-27" in t and "Not legal advice" in t
    for url in ("eur-lex.europa.eu/eli/reg/2024/1689", "eur-lex.europa.eu/eli/reg/2016/679",
                "eur-lex.europa.eu/eli/reg/2022/2554", "ai-act-service-desk.ec.europa.eu", "eiopa.europa.eu"):
        assert url in t, url
    for level in ("**V1**", "**V2**", "**V3**"):
        assert level in t
    assert "not retried" in t and "Publications Office" in t  # honest account of the access problem and the legitimate route
    assert "2 Dec 2027" in t and "2026/1744" in t  # the amended AI Act timeline, not the obsolete one
    assert "Annex III" in t and "claims" in t.lower()


def test_legal_references_separate_obligations_from_engineering_practice():
    t = (GOV / "LEGAL_REFERENCES.md").read_text("utf-8")
    assert "Legal obligations vs engineering practices" in t and "Implemented and tested?" in t


def test_gradio_review_marks_every_finding_with_a_status_and_covers_the_requested_topics():
    t = (GOV / "GRADIO_SECURITY_REVIEW.md").read_text("utf-8")
    for topic in ("Content Security Policy", "Authentication", "In-memory state", "Audit-log integrity"):
        assert topic.lower() in t.lower(), topic
    rows = [x for x in t.splitlines() if x.startswith("| ") and not x.startswith("| Finding") and not x.startswith("|---")]
    assert rows and all(re.search(r"(FIXED\+TESTED|DOCUMENTED|OPEN|FIXED by design)", r) for r in rows if r.count("|") >= 3)
    assert "unsafe-eval" in t and "Error rendering HTML" in t


def test_dependency_report_names_the_accepted_risk_and_the_gaps():
    t = (GOV / "DEPENDENCY_REPORT.md").read_text("utf-8")
    assert "Accepted risk: Pillow" in t and "Exit criteria" in t and "No SBOM" in t and "shared Anaconda" in t
    assert "PILLOW_ADVISORY_REVIEW.md" in t and "accepted_advisories.json" in t

def test_legal_references_record_the_primary_sources_read_and_what_was_not():
    t = (GOV / "LEGAL_REFERENCES.md").read_text("utf-8")
    assert "cellar" in t and "3e485e15-11bd-11e6-ba9a-01aa75ed71a1" in t and "0caf473a-85bd-11ed-9887-01aa75ed71a1" in t
    assert "Art 22" in t and "25 May 2018" in t and "17 January 2025" in t and "Article 4 of Directive 2009/138/EC" in t
    assert "(V3)" in t or "**V3**" in t  # unverified items are still explicitly marked
    assert "No Annex III classification is asserted" in t and "Unresolved; no conclusion is drawn" in t
    assert "Reading was done through a summarising fetch tool" in t  # limits of the verification method


def test_pillow_review_names_the_new_upload_finding_and_the_experiment_limits():
    t = (GOV / "PILLOW_ADVISORY_REVIEW.md").read_text("utf-8")
    assert "104 passed" in t and "unsupported" in t.lower() and "tests do not exercise any Pillow call" in t
    assert "POST /gradio_api/upload" in t and "37" in t
