# Risk assessment (engineering view)

2026-10-27. Qualitative (L = likelihood, I = impact; Low/Med/High) for the **demo as built**, assuming synthetic data and local use.
This is not the risk-management system described in AI Act Art 9 or a DORA ICT risk register; those would be the deployer's/provider's
obligations for a real deployment. "Residual" is after the controls listed, not "zero".

| # | Risk | L | I | Controls in place (evidence) | Residual / gap |
|---|---|---|---|---|---|
| R1 | Wrong or unsupported verdict presented as an answer | Med | High (real use) | Deterministic rules; evidence gate fail-closed; escalation on conflict/exception/neutral clauses; citation validation; mandatory review for non-verdicts. Held-out unsupported-verdict 0.000 lexical / 0.018 semantic (one label dispute) | Self-authored, small, not blind. Unseen wording can still give a wrong *direction*. |
| R2 | Automation bias: reviewers over-trust a "supported" card | Med | High | "Preliminary / not a claim decision" wording; uncertainty and missing-information shown; other passages listed; override path | No reviewer training or process; not user-tested. |
| R3 | Over-abstention makes the tool useless | High | Low-Med | Measured and reported (verdict coverage 0.575 / 0.725); chosen deliberately | Accepted trade-off; improving coverage needs a new pre-registered evaluation. |
| R4 | Prompt injection via policy text or question | Low (no LLM) | Med | Assessor is not steerable by text (tested); tripwire + quarantine + mandatory review; escaping | Tripwire bypassable; **risk returns if an LLM is added**. |
| R5 | Cross-document leakage | Low | High | Default-deny scope, filter, re-check, citation scope; 42-pair negative test; live-server tests | Scope is caller-asserted (no authN/Z). |
| R6 | Unauthorised use / disclosure through the UI | Med if exposed | High | Loopback bind, explicit opt-in for other hosts, container publishes to loopback, headers/CSP | **No authentication**; audit tab global; schema endpoints visible. |
| R7 | XSS via untrusted text | Low | Med | Escaping everywhere (tests, mutation-checked); CSP restricts hosts | CSP needs `unsafe-eval`/`unsafe-inline` (verified), so escaping is the only barrier. |
| R8 | Personal data enters via free text (question, review reason) | Med | Med-High | Question text never stored; reviewer pseudonym enforced; UI warnings | Free-text reasons are stored; no PII detection. |
| R9 | Audit trail altered or lost | Med | Med | Optional hash chain (tested); in-memory runs | Tail truncation/forgery undetected without external anchor; default log is plain text; state lost on restart. |
| R10 | Vulnerable or malicious dependency | Med | Med | Pins + hashes, CI `pip-audit`, Dependabot, ruff `S` rules | **Pillow: 37 advisories (4 critical, 22 high) accepted as a time-boxed, enumerated risk** - no reachable image path, tested compensating controls, expiry 2026-12-31 enforced in CI (`PILLOW_ADVISORY_REVIEW.md`); no SBOM; semantic stack not hash-pinned; container never built here. |
| R11 | Model drift / silent model change | Low | Med | Embedding revision and file checksums verified on load; offline flags | Different hardware/library versions can change vectors slightly; thresholds are model-specific (steep `tau_sem`). |
| R12 | Misleading evaluation claims | Med | Med | Pre-registration, frozen baseline, post-hoc changes logged, limitations in every report | Residual reader misuse; no external review. |
| R13 | Misuse as a decision-maker | Low | High | Disclaimers on every screen, assessment objects and review records | Cannot prevent a deployer from ignoring them. |
| R14 | Availability (single process, no HA) | High | Low (demo) | Health endpoint; container limits | No redundancy, backup or recovery; irrelevant for a demo, essential for production. |
| R15 | Regulatory misclassification | Med | Med | `LEGAL_REFERENCES.md` records what was and was not verified | Legal analysis not done; AI-system status and Annex III position unresolved. |

**Overall:** suitable for a local, single-operator, synthetic-data demonstration. Not suitable for real claims, shared deployment or any
decision with legal or similarly significant effects. Highest-priority gaps before any real use: R6 (authentication/authorisation), R9 (durable, anchored audit),
R8 (data-protection design), R15 (legal analysis), R1/R2 (blind evaluation with real reviewers).
</content>
