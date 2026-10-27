# Release gates - evidence record (2026-10-27)

Only actual evidence is listed. "Not done" means no evidence exists. Nothing here is a certification, a production-readiness claim or a security guarantee.

| Gate | Status | Evidence |
|---|---|---|
| Lexical-only container (runtime target) built and smoke-tested locally | **Done (local)** | `docker build --target runtime`; run with `--read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges -p 127.0.0.1:7860:7860`: uid 10001, `/healthz` `{"status":"ok"}`, CSP and `X-Frame-Options` present, `POST /gradio_api/upload` -> 404 |
| Semantic-mode container built and run locally | **Done (local)** | `docker build --target semantic` (exit 0, image about 1.8 GB; installs torch and sentence-transformers from the package indexes, unpinned by hash - a known gap). Run with the same hardening plus `-v models:/app/models:ro` (mount `rw=false`, read-only rootfs, `CapDrop=[ALL]`, uid 10001, loopback publish): log `Mode: semantic (hybrid) | abstain policy: cal-2026-10-27-v1`, `/healthz` ok, headers present, upload route 404. A call to `DemoService.assess("Wasserschaden", ...)` inside the container returned `POTENTIALLY_COVERED` citing clause 2.2 with no lexical-only notice, i.e. the same HO25 behaviour as the host semantic run. The model was the already-present local copy (no download at build or run). |
| GitHub Actions executed | **Done** | Workflow `CI` has run on `main` for pushes `5b6bdfd`, `9ada03f`, `b9c843d`, `00e1e4a`, `f52bf02`, `a68d706` - all succeeded (jobs: lint/types/tests, known-vulnerability audit with the Pillow allowlist gate, docker build + smoke test of the default lexical target). The 3 real-model tests skip in CI (no model there). Latest: see the Actions tab of this repository (success at the time of writing; the run link belonged to the original private repository). |
| CI covers the semantic container | **No** | CI builds and smoke-tests only the default lexical-only target. |
| Dependabot PR runs | **Open, 4 of 5 failing** | Five Dependabot PRs (#1 safehttpx 0.1.7->0.2.0, #2 pillow 12.3.0->13.0.0, #3 pymupdf 1.27.2.3->2.0, #4 reportlab 5.0.0->5.1.0, #5 pydantic 2.12.5->2.14.1). CI on all five passed lint/tests and the audit job; the `docker build` job failed on four (all except reportlab). Not merged, not closed, not investigated further: the Pillow 13 PR in particular must not be merged without the separate review required by `governance/PILLOW_ADVISORY_REVIEW.md`. |
| Container image vulnerability scan | **Not done** | Docker Scout is installed but the Docker client is not signed in, and a scan would send image metadata to Docker's service; no local scanner (Trivy/Grype) is installed and fetching one needs your approval. No scan result exists. |
| SBOM generation, licence review, penetration test, fuzzing | Not done | |
| Pillow advisory | Unchanged | 37 advisories accepted, time-boxed to 2026-12-31 (`governance/PILLOW_ADVISORY_REVIEW.md`). |

## LF writer validation (fresh clone, `core.autocrlf=true`)
* Lexical-only and semantic paths both exercised: `eval_variants`, `calibrate`, `eval_workflow` run to exit 0 in disposable clones (semantic path used the local model, no download).
* Byte level: no carriage return in any of the six generated artifacts. Git blob hashes (`git hash-object --no-filters`) of the regenerated `abstain_policy.json`, `CALIBRATION_REPORT.md`, `VARIANTS_REPORT.md` and `variants_results.json` equal the committed blobs exactly. `workflow_results.json` / `WORKFLOW_REPORT.md` differ only in timing fields.
* Regression tests `tests/test_eval_writers_lf.py` pass (593 tests total at `a6b3dd9`). Regenerated artifacts were not committed.
