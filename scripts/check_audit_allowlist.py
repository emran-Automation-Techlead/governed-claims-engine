"""Gate for `pip-audit -f json` output: fail on anything that has not been individually reviewed and accepted.

  python scripts/check_audit_allowlist.py AUDIT.json governance/accepted_advisories.json [--today YYYY-MM-DD]

Fails (exit 1) when:
  * any advisory id in the audit is not in the allowlist for that package;
  * a package with accepted advisories is present at a DIFFERENT version than the one reviewed (re-review needed);
  * the allowlist entry has expired (reviews are time-boxed so an accepted risk cannot be forgotten).
Allowlisted ids that no longer appear are reported as stale (informational). Nothing is ignored silently.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


def evaluate(audit: dict, allow: dict, today: date) -> tuple[list[str], list[str]]:
    """Return (failures, notes)."""
    failures: list[str] = []
    notes: list[str] = []
    entries = {e["package"].lower(): e for e in allow.get("accepted", [])}
    seen: dict[str, set[str]] = {}
    for dep in audit.get("dependencies", []):
        name = dep["name"].lower()
        vulns = dep.get("vulns", [])
        if not vulns:
            continue
        entry = entries.get(name)
        if entry is None:
            failures.append(f"{name} {dep['version']}: {len(vulns)} advisory(ies) and no accepted-risk entry: "
                            + ", ".join(v["id"] for v in vulns))
            continue
        if dep["version"] != entry["version"]:
            failures.append(f"{name}: audited version {dep['version']} differs from the reviewed version "
                            f"{entry['version']} - the acceptance does not carry over; re-review")
            continue
        if date.fromisoformat(entry["expires"]) < today:
            failures.append(f"{name}: accepted-risk review expired on {entry['expires']} - re-review")
            continue
        allowed = set(entry["ids"])
        new = [v["id"] for v in vulns if v["id"] not in allowed]
        if new:
            failures.append(f"{name} {dep['version']}: NEW advisory id(s) not covered by the review: " + ", ".join(new))
        seen[name] = {v["id"] for v in vulns}
    for name, entry in entries.items():
        stale = sorted(set(entry["ids"]) - seen.get(name, set()))
        if stale:
            notes.append(f"{name}: {len(stale)} allowlisted id(s) no longer reported (stale): {', '.join(stale[:5])}"
                         + (" ..." if len(stale) > 5 else ""))
        if name in seen and not failures:
            notes.append(f"{name}: {len(seen[name])} advisory(ies) accepted (review expires {entry['expires']}; see {entry['review']})")
    return failures, notes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audit", type=Path)
    ap.add_argument("allowlist", type=Path)
    ap.add_argument("--today", type=date.fromisoformat, default=None)
    a = ap.parse_args(argv)
    failures, notes = evaluate(json.loads(a.audit.read_text("utf-8-sig")), json.loads(a.allowlist.read_text("utf-8-sig")),
                               a.today or date.today())
    for n in notes:
        print("NOTE:", n)
    for f in failures:
        print("FAIL:", f)
    print("audit gate:", "FAILED" if failures else "passed (with the accepted risks listed above)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())