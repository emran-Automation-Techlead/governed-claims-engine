# Governance documents (Milestone 5)

Engineering documentation for a **synthetic-data, offline demonstration**. None of it is legal advice, a certification, an audit result or a
compliance claim. Written 2026-10-27; verify before relying on any statement about law.

| Document | Purpose |
|---|---|
| `LEGAL_REFERENCES.md` | EU AI Act / GDPR / DORA references with source URLs, access dates, **how each was verified (V1/V2/V3)**, and the split between legal obligations and engineering practice |
| `AI_SYSTEM_CARD.md` | What the system is, its purpose, limits, versions, measured behaviour |
| `RISK_ASSESSMENT.md` | Qualitative risk register with controls and residual gaps |
| `THREAT_MODEL.md` | STRIDE-style threats, controls, test evidence, residuals |
| `GRADIO_SECURITY_REVIEW.md` | CSP, authentication, in-memory state, audit integrity, other UI/server findings; each marked FIXED+TESTED / DOCUMENTED / OPEN |
| `PILLOW_ADVISORY_REVIEW.md` | Per-advisory review of the 37 Pillow advisories: severity, affected ranges, exploit prerequisites, reachability evidence, compensating controls, residual risk, conditions under which the app must NOT be exposed, exit criteria (table generated from `pillow_advisories.json`; allowlist in `accepted_advisories.json`) |
| `DEPENDENCY_REPORT.md` | pip-audit results before/after, upgrades made, accepted Pillow risk, supply-chain gaps |
| `AUDIT_SCHEMA.md` | Audit and review record fields, optional hash chain, limits |
| `EVALUATION_PROTOCOL.md` | Data-set roles, metrics, pre-registration, validity limits |
| `OPERATIONAL_RESILIENCE.md` | Practices through a DORA lens and what is missing |
| `DATA_PROTECTION.md` | What data the demo touches and what GDPR work real data would require |

Related: `../SECURITY_LIMITATIONS.md`, `../eval/PREREGISTRATION.md`, `../eval/m3/M3_FINDINGS.md`, `../docs/DEMO_WALKTHROUGH.md`.
</content>
