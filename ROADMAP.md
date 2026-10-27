# ROADMAP
Each milestone ends with: changed files, tests run, actual outcomes, risks, next step. Nothing past M5 is started.

- M1 [DONE, APPROVED]: scaffold, schemas, secure PDF ingestion, BM25, synthetic policies.
- M2 [DONE, APPROVED]: page/clause-aware chunking, multilingual tokenizer, hybrid RRF retrieval, pinned local multilingual model, labelled benchmark (frozen baseline in `eval/baseline_m2/`).
- M3 [DONE, APPROVED]: LangGraph workflow, deterministic assessor, calibrated abstention, citation/scope/injection controls, review/audit library, calibration/held-out/adversarial datasets, pre-registration.
- M4 [DONE, APPROVED]: offline Gradio demo on the unchanged cautious baseline, reviewer workflow, audit viewer, real-browser verification, walkthrough + screenshots (preserved).
- **M5 [DOCUMENTATION AND DEPENDENCY REVIEW COMPLETE 2026-10-27 - AWAITING YOUR APPROVAL; container verification NOT DONE]**:
  - Done and verified: governance documents (11 + Pillow review), legal references with V1/V2/V3 verification levels, Gradio security review (found and fixed: error-text leak, unauthenticated upload route), dependency upgrades and `pip-audit`, time-boxed enumerated Pillow acceptance enforced by a CI gate, opt-in hash-chained audit log, 588 tests (venv) / 585+3 skipped (shared env), ruff + security rules + mypy + `pip check` clean.
  - Update 2026-10-27 (after this M5 text was written): `Dockerfile` runtime and semantic targets were built and smoke-tested locally; `.github/workflows/ci.yml` has run on GitHub (green on `main`; lexical target only); Dependabot opened 5 PRs (4 with failing docker-build jobs, not merged). Image vulnerability scan, SBOM and compose profile runs are NOT done. Evidence: `docs/RELEASE_GATES.md`.
  - **Gate before any container claim:** you start Docker Desktop and authorise the build + smoke test (`docker build --target runtime`, hardened run, `/healthz`, page, headers, non-root, no model in image). I will not start Docker myself.
- M6 (PROPOSED, not started): AWS deployment *proposal and cost estimate only* (region/service availability check, IAM least privilege, budget guardrails, cleanup plan). **No provisioning without explicit approval**; AWS connector unavailable, only the read-only `portfolio-readonly` CLI profile exists. Prerequisite worth settling first: authentication/authorisation design (the demo has none) and a decision on Pillow (needs a Gradio release permitting Pillow 13, or a different UI layer).
- M7: video: script -> your approval -> voice-service narration in sections (after confirming credits) -> screen recordings of the real app -> ffmpeg assembly + SRT from real audio durations.

## Open items carried forward (with owners/dates where they exist)
| Item | State |
|---|---|
| Docker build + smoke test | blocked on you starting Docker Desktop |
| Pillow 37 advisories | accepted until **2026-12-31** (CI fails afterwards); exit = Pillow >= 13.0.0 via a Gradio release that permits it, or replace the UI framework |
| Authentication / authorisation, per-user trace ownership, durable + anchored audit storage, rate limiting | not built; required before any shared or real-data use |
| Legal analysis | AI-system status and Annex III position unresolved; GDPR Art 22 guidance (WP251rev.01) not read; Luxembourg CNPD/CAA not researched; DORA Art 2(3)(b) applicability undetermined; confirm exact OJ wording before quoting |
| CI on GitHub | first real run pending (needs the project as its own repository root) |
| Low answer coverage (by design), non-blind evaluation, no stemming, no real-document evaluation | unchanged |