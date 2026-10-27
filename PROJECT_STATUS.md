# PROJECT_STATUS (after Milestone 5, 2026-10-27)

Prototype on synthetic data only. **Not production-ready. Not legally certified. No compliance claim and no definitive legal classification.**
Nothing committed to git. No AWS resources, no paid API calls, no voice-service credits. The shared Anaconda environment was never modified.

## Milestone 5 status
**Documentation and dependency review: COMPLETE.** **Container verification: NOT DONE and explicitly deferred** - the Docker daemon is not running; Docker Desktop was not started
(per instruction) and the image has **never been built or run**. M5 awaits your approval; Docker build + smoke test await your go-ahead.

## 1. VERIFIED (executed in this session)
| Check | Result |
|---|---|
| Tests, project venv | **588 passed, 0 failed, 0 skipped** (~90 s). 474 earlier + **114 new** (audit chain 15, container/CI config 32, governance docs 29, dependency governance 19, demo app +19) |
| Tests, shared Anaconda env (older Gradio 6.10.0 / Starlette 0.52.1 / pytest 7.4.0, left untouched) | 585 passed, 3 skipped (the real-model tests; no embedding package there) |
| `ruff check .` and `ruff check --select S src scripts` (bandit-equivalent rules) | pass |
| `mypy src` (26 files) / `pip check` | no issues / no broken requirements |
| Dependency audit (`pip-audit 2.9.0`, isolated venv) | container closure and project venv: **only Pillow 12.3.0 (37 advisories) remains**; Gradio 6.10.0 (3), Starlette 0.52.1 (5), pip (7), pytest 7.4.0 (1) fixed by upgrades (Gradio 6.30.0, Starlette 1.10.0, pip, pytest 9.0.3) |
| Allowlist gate on the real audit | passes the reviewed state; **fails** when one advisory id is removed from a copy (checked both ways) |
| Frozen baselines and application behaviour | M2 baseline files, case files and calibrated policy byte-identical (hash-checked); `VARIANTS_REPORT.md` byte-identical and every workflow outcome (status, citations, flags) identical after the dependency upgrades; assessor/thresholds/retrieval modules untouched since M3 |
| Browser (Chrome) | UI renders and works on Gradio 6.30.0, no console errors; CSP experiment: removing `unsafe-eval` breaks every `gr.HTML` panel (so the CSP must keep it) |
| Live server probes | found and fixed: `show_error=True` leak; unauthenticated `POST /gradio_api/upload` (200) - now blocked with file/icon routes; verified with a unique-marker test that, with the block disabled, an upload really lands on disk |
| Mutation checks (deliberate breakage, suite must fail) | more than 45 across M3-M5; M5: host guard, audit chain (prev/seq/hash/resume), Dockerfile (root user, no hashes, tag-only base, model fetch, secret, models copied, no healthcheck), `.dockerignore`, CI (unpinned action, write permission, credential persistence, missing mypy), compose (all-interfaces publish), `show_error`, upload block, component-type guard - all caught (one equivalent mutant noted) |

## 2. PARTIAL checks (do not read these as full verification)
* **Container requirements:** all 76 hash-pinned Linux wheels (cp311, manylinux x86_64) were downloaded and matched their pinned hashes under `--require-hashes`. That is **not a build**; pip evaluates markers for the Windows host, so a Linux-only dependency could be missing (the Dockerfile fails loudly if so - unexercised).
* **Dockerfile / compose / CI:** verified only by static tests (structure, pinning, non-root, no secrets, no model download) and by parsing the YAML. (Superseded 2026-10-27: the workflow has since run on GitHub and the Docker targets have been built and smoke-tested locally - see `docs/RELEASE_GATES.md`; image vulnerability scan is still not done.)
* **Legal references** (`governance/LEGAL_REFERENCES.md`): GDPR and DORA provisions read in the Official Journal text via the Publications Office (V1) through a *summarising* fetch tool - exact wording should be confirmed in the OJ; AI Act provisions read on the Commission's Service Desk consolidated text (V1, non-binding presentation); amending Regulation (EU) 2026/1744 read only for title and recitals (operative articles not reached); some items remain V2/V3 and are marked.
* **Pillow reachability:** static review of Gradio source + live probing + a tested component guard. Not a proof; depends on Gradio 6.30.0 internals and on the controls staying in place.
* **Pillow 13.0.0 experiment:** 104 demo tests passed in a throw-away venv with Pillow 13.0.0 over Gradio 6.30.0, but that is outside Gradio's declared range (`pillow<13`), the tests exercise no image code, and the venv was discarded. Not adopted.

## 3. NOT RUN
Container image vulnerability scan (Docker build/run and GitHub Actions were later done - see `docs/RELEASE_GATES.md`); SBOM generation; licence review; load, fuzz or penetration testing; any real-document evaluation; any test with real reviewers; authentication; durable audit storage; AWS anything; video.

## 4. Pillow findings (details: `governance/PILLOW_ADVISORY_REVIEW.md`)
37 advisories, **4 CRITICAL, 22 HIGH, 11 MODERATE**, each listed individually (id, OSV CVE alias, severity, CVSS vector, affected range, surface, prerequisite). All fixed **only in 13.0.0**; Gradio 6.30.0 (latest) requires `pillow<13`; no 12.x fix.
**Accepted as a time-boxed, enumerated risk (expires 2026-12-31, enforced in CI) - not "resolved".** No image-decoding path is reachable through the app as built and served; compensating controls (no image/file components - tested; upload/file/icon routes blocked - tested; no project use of PIL) are what the acceptance rests on, **not** loopback binding.
**Must NOT be exposed** to untrusted networks, or used with real data, if: an image/file/media component is added; the route blocks are removed; connector/workflow/model pipelines are enabled; any code processes images; the container is unverified and intended beyond local testing; there is no authentication in front; or the audit gate reports anything outside the allowlist / the acceptance has expired.

## 5. Changed / new files (Milestone 5)
Code: `src/claims_engine/audit_chain.py` (new), `app.py` (host guard, `/healthz`, `show_error=False`, blocked routes, `--host`, `--tamper-evident`), `demo_service.py`, `render.py`, `retrieval.py`, `fetch_model.py` (assert/URL-scheme hardening). Config: `Dockerfile`, `.dockerignore`, `compose.yaml`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `requirements-container.txt` (new, hash-pinned), `requirements-demo/dev/embeddings/lock`, `pyproject.toml` (ruff `S`). Scripts: `scripts/make_container_requirements.py`, `check_audit_allowlist.py`, `pillow_advisory_review.py`. Governance (11 documents + `pillow_advisories.json`, `accepted_advisories.json`). Tests: `test_audit_chain`, `test_container_and_ci_config`, `test_governance_docs`, `test_dependency_governance` (+ demo app additions). The M4 walkthrough and the three screenshots are preserved (screenshots were captured on Gradio 6.10.0; UI re-checked on 6.30.0).

## 6. Remaining risks (highest first)
1. **Container never built/run** - every container property is a claim about files, not an observation.
2. Pillow: 37 accepted advisories incl. 4 critical; protected by controls that must stay in place; expires 2026-12-31.
3. **No authentication/authorisation**; audit tab global across sessions; schema endpoints visible; no rate limiting.
4. CSP requires `unsafe-eval`/`unsafe-inline` (verified), so HTML escaping is the only XSS barrier.
5. Review state in memory; audit log tamper-*evident* only with an external anchor that does not exist.
6. Legal analysis is not done: AI-system status and Annex III position unresolved; GDPR Art 22 "meaningful human involvement" guidance not read; Luxembourg authorities not researched; DORA Art 2(3)(b) applicability to a given insurer undetermined.
7. Evaluation remains self-authored and not blind; abstention-heavy baseline (unchanged by design).
8. CI untested on GitHub; shared Anaconda environment still contains advisory-affected packages (untouched by design).

## 7. Recommended next steps (need your approval; nothing started)
(a) You start Docker Desktop and authorise the build + smoke test (the CI container steps, run locally). (b) M6: AWS deployment *proposal and cost estimate only*. (c) Video production only after a script is approved.