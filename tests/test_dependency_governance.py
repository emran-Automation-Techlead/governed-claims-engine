"""The accepted-risk machinery for the Pillow advisories: data snapshot, rendered review, allowlist gate."""
import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_audit_allowlist as gate
import pillow_advisory_review as review

SNAP = json.loads((ROOT / "governance" / "pillow_advisories.json").read_text("utf-8"))
ALLOW = json.loads((ROOT / "governance" / "accepted_advisories.json").read_text("utf-8"))
TODAY = date(2026, 10, 27)


def audit(version="12.3.0", ids=None, extra=None):
    ids = ids if ids is not None else [a["id"] for a in SNAP["advisories"]]
    deps = [{"name": "pillow", "version": version, "vulns": [{"id": i} for i in ids]}]
    deps += extra or []
    return {"dependencies": deps}


# ---------------------------------------------------------------- snapshot facts
def test_snapshot_records_every_advisory_individually_with_severity_range_and_fix():
    rows = SNAP["advisories"]
    assert len(rows) == 37 and len({r["id"] for r in rows}) == 37
    assert SNAP["pillow_version"] == "12.3.0" and SNAP["retrieved_utc"] == "2026-10-27"
    for r in rows:
        assert r["id"].startswith("GHSA-") and r["severity"] in {"CRITICAL", "HIGH", "MODERATE", "LOW"}
        assert r["cvss"].startswith("CVSS:") and r["summary"] and r["published"].startswith("2026-")
        assert r["fixed"] == "13.0.0"  # no advisory is fixed in a 12.x release


def test_every_advisory_affects_the_pinned_version():
    def v(s):
        return tuple(int(x) for x in s.split("."))

    for r in SNAP["advisories"]:
        assert v(r["introduced"]) <= v("12.3.0") < v(r["fixed"]), r["id"]


def test_severity_counts_are_as_documented():
    from collections import Counter

    assert Counter(r["severity"] for r in SNAP["advisories"]) == {"HIGH": 22, "MODERATE": 11, "CRITICAL": 4}


def test_snapshot_is_ordered_most_severe_first():
    ranks = [review.SEV_RANK[r["severity"]] for r in SNAP["advisories"]]
    assert ranks == sorted(ranks)


# ---------------------------------------------------------------- generated review document
def test_review_table_matches_the_snapshot():
    assert review.table_in_doc() == review.render(SNAP)
    assert review.main(["--check"]) == 0


def test_review_table_lists_all_ids_and_no_row_claims_reachability():
    table = review.table_in_doc()
    assert all(r["id"] in table for r in SNAP["advisories"])
    assert table.count("**No** (see section 3)") == 37


def test_every_summary_is_classified_by_a_specific_rule():
    assert all(review.classify(r["summary"])[0] != "other" for r in SNAP["advisories"])
    assert review.classify("something unrelated")[0] == "other"


def test_review_document_states_residual_risk_conditions_and_exit_criteria():
    t = (ROOT / "governance" / "PILLOW_ADVISORY_REVIEW.md").read_text("utf-8")
    for needle in ("must NOT be exposed", "Compensating controls", "Exit criteria", "not a patched", "expires",
                   "Reachability", "unauthenticated upload"):
        assert needle.lower() in t.lower(), needle


# ---------------------------------------------------------------- allowlist
def test_allowlist_covers_exactly_the_reviewed_snapshot():
    entry = ALLOW["accepted"][0]
    assert entry["package"] == "pillow" and entry["version"] == SNAP["pillow_version"]
    assert set(entry["ids"]) == {r["id"] for r in SNAP["advisories"]}
    assert date.fromisoformat(entry["expires"]) > date.fromisoformat(entry["reviewed"])
    assert (ROOT / entry["review"]).exists()


def test_gate_passes_for_the_reviewed_state():
    failures, notes = gate.evaluate(audit(), ALLOW, TODAY)
    assert failures == [] and any("37 advisory" in n for n in notes)


def test_gate_fails_on_a_new_pillow_advisory():
    failures, _ = gate.evaluate(audit(ids=[*[a["id"] for a in SNAP["advisories"]], "GHSA-new-new-new"]), ALLOW, TODAY)
    assert failures and "GHSA-new-new-new" in failures[0]


def test_gate_fails_on_any_other_package_with_advisories():
    other = [{"name": "starlette", "version": "1.10.0", "vulns": [{"id": "PYSEC-2099-1"}]}]
    failures, _ = gate.evaluate(audit(extra=other), ALLOW, TODAY)
    assert any("starlette" in f and "PYSEC-2099-1" in f for f in failures)


def test_acceptance_does_not_carry_over_to_another_pillow_version():
    failures, _ = gate.evaluate(audit(version="12.4.0"), ALLOW, TODAY)
    assert failures and "re-review" in failures[0]


def test_acceptance_expires():
    failures, _ = gate.evaluate(audit(), ALLOW, date(2027, 1, 1))  # after the 2026-12-31 expiry
    assert failures and "expired" in failures[0]


def test_fixed_advisories_are_reported_stale_not_failed():
    failures, notes = gate.evaluate(audit(ids=[]), ALLOW, TODAY)
    assert failures == [] and any("stale" in n for n in notes)


def test_gate_cli_exit_codes(tmp_path, capsys):
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps(audit()), "utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(audit(ids=["GHSA-x"])), "utf-8")
    allow = str(ROOT / "governance" / "accepted_advisories.json")
    assert gate.main([str(ok), allow, "--today", "2026-10-28"]) == 0
    assert "passed" in capsys.readouterr().out
    assert gate.main([str(bad), allow, "--today", "2026-10-28"]) == 1
    assert "FAILED" in capsys.readouterr().out
    assert gate.main([str(ok), allow, "--today", "2027-02-01"]) == 1  # expired


@pytest.mark.parametrize("snippet", ["check_audit_allowlist.py audit.json governance/accepted_advisories.json",
                                     "pillow_advisory_review.py --check", "-f json -o audit.json"])
def test_ci_runs_the_allowlist_gate_and_the_document_check(snippet):
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8")
    assert snippet in ci