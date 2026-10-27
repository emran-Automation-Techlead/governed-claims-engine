# AI system card - Governed Claims Coverage Engine (prototype)

Version 0.1.0 (Milestone 5), 2026-10-27. Synthetic data only. **Not production-ready, not legally certified, no compliance claim.**
Whether this software is an "AI system" under Regulation (EU) 2024/1689 is **unresolved** (see `LEGAL_REFERENCES.md` section 5).

## 1. Intended purpose
A local, offline **demonstration** of governed decision support: given a question about *synthetic* insurance policies and the documents the
user selected, it returns a *preliminary* clause-level reading (potentially covered / potentially excluded / insufficient evidence /
human review required) with exact citations, or declines. Every output is a proposal for a human reviewer.

**Out of scope / must not be used for:** real claims or real policyholders; any binding coverage, claims or payout decision; automated
decisions without a person; underwriting, risk assessment, pricing or profiling of individuals; processing personal data; any production service.

## 2. Components and versions
| Component | Detail |
|---|---|
| Ingestion | PyMuPDF text extraction; type/magic/size/page-count/encryption checks; SHA-256, doc id, version; empty-page handling |
| Retrieval | page- and clause-aware chunks; in-house BM25; optional vector search with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (Apache-2.0, revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, checksum-verified local copy, never downloaded automatically); reciprocal-rank fusion |
| Workflow | LangGraph: validate -> screen question -> scoped retrieve -> scope re-check -> screen evidence -> evidence-support gate -> deterministic assess -> citation validation (bounded retry) -> abstain/review gate -> audit |
| Assessor | `rules-1.0.0`: deterministic EN/FR/DE cue rules; **no language model, no network, no cost** |
| Abstention policy | `cal-2026-10-27-v1`: `tau_lex = 0.5`, `tau_sem = 0.66`, fitted on 64 labelled calibration cases; fails closed if the file is missing |
| Guardrails | keyword/regex injection tripwire (bypassable), quarantine of suspicious passages, document-scope enforcement, citation validator |
| Review & audit | approve/override (explanation required); audit records of ids/hashes; optional hash-chained log |
| UI | Gradio 6.30.0, loopback only, no uploads, no authentication |

## 3. Data
Eight fictional policies (home/travel/motor in EN, FR, DE, plus one deliberately poisoned test document). No real personal or
proprietary data. The embedding model's own training data was not assessed. Evaluation sets are small and author-written
(calibration 64, held-out 55, adversarial 19, plus the frozen 52-case M2 set).

## 4. Measured behaviour (all offline; see `eval/` for generated reports)
* Retrieval (frozen M2 baseline, 49 answerable cases): Recall@5 BM25 0.837, vector 0.867, hybrid 0.939.
* Workflow, held-out (n=55), lexical-only / semantic: acceptable-status rate 0.855 / 0.891; unsupported-verdict rate 0.000 / 0.018; wrong-direction verdicts 0 / 0;
  verdicts issued on 57.5 % / 72.5 % of cases whose label was a verdict; the rest abstained or escalated.
* Adversarial (n=19): 8/8 query injections flagged; 2 paraphrased injections not flagged but produced no verdict; 0 cross-document leaks; 0 citation failures.
* **These are not performance claims about real policies.** Same author wrote system, data and labels; no blind test; no significance tests; categories have 2-8 cases.

## 5. Known limitations
Cautious by design (abstains on most paraphrase and cross-language questions in lexical mode); hand-written cue lexicon will misclassify unseen wording;
no stemming; German compounds weak; keyword screening is bypassable; no authentication; in-memory review state; no real-document evaluation; see `SECURITY_LIMITATIONS.md`,
`GRADIO_SECURITY_REVIEW.md`, `eval/m3/M3_FINDINGS.md`.

## 6. Human oversight
No result is final. Abstentions, escalations, flagged cases and all non-verdict outcomes are marked *mandatory review*; verdict outcomes are *standard review*.
A reviewer can approve or override (with a required explanation); the original proposal is preserved. UI wording states every output is preliminary and not a claim
decision. Automation-bias mitigation is wording and design only - **no training, no process controls, not evaluated with real reviewers**.

## 7. Change control
Behaviour is frozen by tests and hashes: M2 baseline (`eval/baseline_m2`, SHA-256 checked), case files and the calibrated policy (hashes recorded in `eval/m3/INPUT_HASHES.txt`),
assessor/thresholds unchanged since Milestone 3. Dependencies pinned (container: version + SHA-256 of every wheel).
</content>
