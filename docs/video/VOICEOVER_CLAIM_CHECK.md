# Voiceover claim check (updated 2026-10-27, after re-run)

Each factual claim in `VOICEOVER_SCRIPT.md` against the repository. "Checked" = read in code/tests/reports. "Re-run" = reproduced by commands run on 2026-10-27 (see section 2).

## 1. Claim table

| Ch | Claim | Evidence | Result |
|---|---|---|---|
| C02 | 8 synthetic PDFs, one deliberately poisoned | `data/policies` (4), `data/heldout` (3), `data/adversarial/synthetic_poisoned_policy.pdf` (1) | Checked |
| C02 | Assessor is deterministic rules, not an LLM | `assessor.py`; `eval/m3/M3_FINDINGS.md` | Checked |
| C05 | Node order | `workflow.py` lines 301-312; the re-run traces in `workflow_results.json` show `validate_input, screen_query, retrieve, enforce_scope, screen_evidence, score_evidence, assess, validate_citations, human_review_gate, audit` (abstain branch replaces assess/validate_citations) | Checked + re-run |
| C05 | Scope enforced three times | (1) search filtered by `doc_ids` (`workflow.py:149`); (2) `enforce_scope` re-filter (`:153-158`, `scope_violation` flag); (3) `citations.py:49` `out_of_scope`. Matches `THREAT_MODEL.md`. Re-run: cross-document leaks 0 | Checked + re-run |
| C07 | Each citation field has a failing-case test | `tests/test_citations.py` parametrized: chunk id, doc id, SHA-256, version, page, clause, quote; scope in a separate test. Full suite re-run green | Checked + re-run |
| C09 | 64 calibration / 55 held-out / 19 adversarial | input hashes in re-run `workflow_results.json`; `M3_FINDINGS.md` | Re-run (counts); hashes of case files match `policy.calibration_cases_sha256` |
| C09 | Held-out acceptable 0.855 (lexical) / 0.891 (semantic) | Re-run; identical to committed (section 2) | **Re-run, reproduced** |
| C09 | Unsupported-verdict 0.000 / 0.018 (HO25, semantic only) | Re-run | **Re-run, reproduced** |
| C09 | Verdict coverage 0.575 / 0.725 | Re-run | **Re-run, reproduced** |
| C09 | Pre-fix rates 0.836 / 0.855 after German-cue fix | `WORKFLOW_REPORT_run1_prefix.md`, `M3_FINDINGS.md` section 5 | **Copied from committed report; not re-run** (the pre-fix code state is not reproducible without reverting the fix) |
| C09 | Not blind, self-authored | `M3_FINDINGS.md`, `EVALUATION_PROTOCOL.md` | Checked |
| C09 | Retrieval baseline frozen and checksummed | `eval/baseline_m2/`, `tests/test_baseline_frozen.py`; re-run reproduces the frozen M2 numbers (tests green) | Checked + re-run |
| C10 | 37 Pillow advisories: 4 critical, 22 high, 11 moderate; fixed only in 13.0.0; Gradio requires pillow<13 | `PILLOW_ADVISORY_REVIEW.md` section 1; allowlist gate re-run (below) | Checked + re-run (gate, using the audit JSON captured earlier on 2026-10-27; pip-audit itself was not re-run) |
| C10 | Accepted, time-boxed to 2026-12-31 | same | Checked |
| C10 | Check script runs in CI and has passed | `.github/workflows/ci.yml`; GitHub Actions runs on `main` all green (run 40474361481 and earlier; `docs/RELEASE_GATES.md`). **Correction:** earlier versions of this file and the script said CI had never run; that was wrong - Actions had been running on every push | Corrected 2026-10-27 |
| C10 | No authentication, in-memory state, global audit tab, CSP needs unsafe-eval, keyword screen bypassable | `GRADIO_SECURITY_REVIEW.md`, `SECURITY_LIMITATIONS.md` | Checked |
| C11 | Container evidence (lexical-only runtime image) | Docker run 2026-10-27: uid 10001, read-only, cap-drop ALL, loopback publish, `/healthz` ok, headers, upload 404 | Verified earlier today; **not repeated in this pass** (Docker not re-run) |
| C11 | Semantic container run once locally; image vuln scan outstanding; CI covers lexical image only | `docs/RELEASE_GATES.md` | Script updated |
| C11 | AWS only proposed; credit balance unverified | `docs/AWS_DEPLOYMENT_PLAN.md` | Checked |
| C12 | Reproducibility | See section 3 | Narrowed |

## 2. Re-run record (2026-10-27, project venv, Windows, Python 3.11.7, no network, no paid calls)

| Command | Exit | Result |
|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | 0 | **588 passed, 0 skipped** (the 3 skips seen in a fresh clone were the model-dependent tests; they ran here because the pinned model is present locally) |
| `python -m ruff check src tests scripts` and `--select S src` | 0 | all checks passed |
| `python -m mypy src` | 0 | no issues in 26 source files |
| `python -m pip check` | 0 | no broken requirements |
| `python scripts/check_audit_allowlist.py <audit.json> governance/accepted_advisories.json` | 0 | passed with 37 accepted Pillow advisories (audit JSON from earlier today) |
| `python -m claims_engine.eval_variants` (lexical + semantic) | 0 | `VARIANTS_REPORT.md` and `variants_results.json` **byte-identical** to committed |
| `python -m claims_engine.calibrate` (lexical + semantic) | 0 | policy content identical (`cal-2026-10-27-v1`, tau_lex 0.5, tau_sem 0.66, same case-file hash); report identical after line-ending normalisation |
| `python -m claims_engine.eval_workflow` (lexical + semantic) | 0 | `workflow_results.json` identical except per-row timing keys; `WORKFLOW_REPORT.md` differs only in four mean-latency lines |

Semantic runs used the locally present pinned model (`models/paraphrase-multilingual-MiniLM-L12-v2`, revision e8f8c211226b894fcb81acc59f3b34ba3efd5f42); nothing was downloaded, and the loader verifies the manifest checksums on load.

**Housekeeping finding:** the generators overwrite committed files. On Windows `calibrate` rewrote `calibration/abstain_policy.json` with CRLF line endings (content unchanged), which would break the byte-exact frozen-policy tests. I saved the outputs to a temp folder, restored the committed files with `git checkout`, re-ran the frozen tests (20 passed) and confirmed a clean working tree. Recommendation: make the writers use `newline="\n"` (a code change, not made here).

Not re-run in the evaluation pass: Docker smoke test, pip-audit itself (network). Image scan: not done. GitHub Actions: had already run (see C10 correction). New wall-clock latency values differ from committed ones (different machine load); no metric changed.

## 3. Reproducibility statement supported by the evidence
* Tests, lint and typing: `python -m pytest -q`, `ruff`, `mypy` (lexical-only machines skip the 3 model-dependent tests).
* Lexical evaluation: `python -m claims_engine.eval_variants --no-semantic`, `eval_workflow --no-semantic` (README).
* Semantic results: additionally need `python -m claims_engine.fetch_model` (deliberate, pinned, checksum-verified download).
* Caveat: the generators overwrite the committed reports, and on Windows may change line endings.

## 4. HO25 label review (no change made)
* Case (`eval/heldout_cases.jsonl` line 25): query `Wasserschaden` (one word, "water damage"), German home policy; `relevant: [synthetic_home_policy_de.pdf#1.2]`; `primary: human_review_required`; `acceptable: [human_review_required, insufficient_evidence]`.
* Re-run: lexical abstained (`insufficient_evidence`, acceptable). Semantic returned `potentially_covered` citing clause 2.2 -> counted as the single unsupported verdict (0.018 = 1/55). Citation validation passed (no errors, no leaks).
* Clause 1.2 is a definition of *Leitungswasserschaden* (sudden escape of water from fixed pipes); clause 2.2 *Leitungswasser* is the coverage clause for sudden pipe bursts.
* Assessment: the query is underspecified (no scenario), so a cautious label is defensible; but the system cited a real, on-topic coverage clause that the label did not list as relevant, and it said "potentially" (a hedged status) with mandatory-review semantics intact. Reasonable reviewers could differ. The `relevant` list also omits 2.2.
* Recommendation: **do not change the label silently.** Open a separate, reviewable change that (a) keeps the original result recorded as "first-run label", (b) decides whether `potentially_covered` is acceptable for single-word queries, and (c) is declared post-hoc in `M3_FINDINGS.md` like the German-cue fix. Changing it would move the semantic unsupported rate 0.018 -> 0.000, so any such change must be disclosed as label revision after seeing results. Script wording: "its label is debatable; flagged for separate review".

## 5. Unresolved
* Container evidence in C11 was gathered earlier today and not repeated in this pass.
* pip-audit not re-run (needs network); the gate used earlier output.
* Writers' line-ending behaviour (section 2) not fixed.
