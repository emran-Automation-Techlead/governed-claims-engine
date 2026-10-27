# Operational resilience (engineering practices viewed through a DORA lens)

**DORA (Regulation (EU) 2022/2554) obliges in-scope *financial entities* and, by contract, their ICT third-party providers; it does not make a code
repository compliant, and nothing here claims DORA compliance.** Scope is entity-based and has carve-outs (see `LEGAL_REFERENCES.md` section 4;
article-level details there are mostly unverified V3). This page lists practices that would *help* an insurer that adopted such software, and what is missing.
Pillars named by EIOPA: ICT risk management, incident reporting, resilience testing, third-party risk, information sharing.

| Pillar | Practice in this repo | Evidence | Missing for a real deployment |
|---|---|---|---|
| ICT risk management - asset/dependency inventory | Pinned requirements, full lock file, hash-pinned container closure (76 wheels), pinned base-image digest | `requirements-*.txt`, `Dockerfile`, config tests | No SBOM; no ownership/criticality classification; no risk register tied to business functions |
| ICT risk management - change control | CI gate (ruff, ruff security rules, mypy, pytest 533+ tests, pip check), mutation checks, frozen baselines with hashes | `.github/workflows/ci.yml` (not yet run on GitHub), local runs | No review/approval workflow, no release management, no rollback procedure |
| Protection and prevention | Non-root read-only container, no capabilities, loopback publish, scope enforcement, escaping, strict CSP (with documented `unsafe-eval`), offline model loading with checksums | `GRADIO_SECURITY_REVIEW.md` | No authentication, rate limiting, WAF, secrets management (none needed today), image scanning |
| Detection | Health endpoint, structured audit records, guardrail flags, opt-in hash chain | `/healthz`, `AUDIT_SCHEMA.md` | No monitoring/alerting, no log shipping, no anomaly detection |
| Response and recovery / backup | None: demo is stateless and in-memory | - | Backup/restore, RTO/RPO, failover, incident runbooks |
| Incident reporting | Not applicable to a demo | - | Classification and notification procedures required of the entity |
| Resilience testing | Unit/integration/adversarial tests, more than 40 deliberate-breakage (mutation) checks across milestones, live-server tests, network-blocked tests | `tests/` | No load, chaos, failover or threat-led penetration testing |
| Third-party / supply-chain risk | Minimal runtime dependencies; no cloud services at run time; model fetched once, deliberately, checksum-verified; CI audit + Dependabot | `DEPENDENCY_REPORT.md` | No vendor assessment, exit strategy or contract terms (e.g. DORA Art 30) because no provider relationship exists |
| Information sharing | None | - | Participation/sharing arrangements are entity-level |

## Operating the demo (non-production)
* Local: `python -m claims_engine.app`; Docker (when a daemon is available): `docker build --target runtime -t claims-demo .` then
  `docker run --rm -p 127.0.0.1:7860:7860 --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges claims-demo`.
  **Docker was not available during Milestone 5; the image has not been built or run.** The CI `container` job is designed to do that.
* Health: `GET /healthz` -> `{"status":"ok"}`. Logs: stdout only; no secrets are read or written.
* Cost: no cloud resources exist; nothing is provisioned. A future AWS design is a separate, approval-gated milestone.
</content>
