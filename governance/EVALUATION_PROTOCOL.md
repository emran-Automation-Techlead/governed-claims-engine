# Evaluation protocol

Everything here is **offline** (no live-model evaluation exists: there is no language model). Costs are $0 per assessment. Source files:
`eval/PREREGISTRATION.md`, `eval/m3/M3_FINDINGS.md`, generated reports under `eval/` and `calibration/`.

## 1. Data sets and roles
| Set | File | Cases | Role | Rules |
|---|---|---|---|---|
| M2 retrieval baseline | `eval/baseline_m2/` (frozen, SHA-256 in `SHA256SUMS`, `.gitattributes -text`) | 52 | Historical baseline; reproduced, never overwritten | guarded by `tests/test_baseline_frozen.py` |
| Calibration | `eval/calibration_cases.jsonl` | 64 (36 answerable, 28 unanswerable) | choose abstention thresholds only | queries disjoint from all other sets (tested); policy file records the set's SHA-256 (tested) |
| Held-out | `eval/heldout_cases.jsonl` | 55 | measure the workflow after thresholds were frozen | 3 documents unseen in calibration |
| Adversarial | `eval/adversarial_cases.jsonl` | 19 | injection (query and document), paraphrased bypass, cross-document lures | one poisoned test document |

## 2. Method
1. Decision rules (adoption of stopwords/subwords, threshold choice and margin, no re-tuning after viewing held-out) are written **before** the runs (`eval/PREREGISTRATION.md`).
2. Retrieval metrics are clause-level: Recall@1/3/5, Hit@5, MRR; relevance = (document, clause id) in the labelled set; multiple chunks of one clause collapse.
3. Workflow metrics: status accuracy (== primary label), acceptable-status rate (label sets allow genuine ambiguity), verdict rate and coverage on verdict-labelled cases,
   **unsupported-verdict rate** (a verdict outside the acceptable set), wrong-direction verdicts, abstention quality, over-abstention, independent citation re-validation,
   cross-document leaks, question text in audit records, latency.
4. Abstention threshold rule: smallest grid value with zero false accepts on the unanswerable calibration cases, plus one grid step. The rule-of-three bound (~11 % with 0/28) is reported next to it.
5. Reproduction: `python -m claims_engine.eval_variants | calibrate | eval_workflow` (add `--no-semantic` for lexical-only). Outputs are generated files; the M2 baseline arm must reproduce the frozen numbers (checked in the report).

## 3. Validity limits (state these whenever a number is quoted)
Same author wrote documents, queries, labels, cue lexicon and stopword lists; the held-out set is *not blind*; categories hold 2-8 cases; no significance tests;
labels HO25 and Q37 are arguably too strict; one post-hoc cue fix (German `übernehmen`) made HO18/HO21 no longer held-out; one adversarial query was reworded to
remove an overlap; thresholds are specific to this corpus and embedding model (the semantic threshold is steep); latency is single-process CPU on one machine.

## 4. Mutation checking (test-suite quality, not model quality)
Safety-critical code paths were deliberately broken one at a time and the suite had to fail: workflow/citation/scope/quarantine/gate rules (13), demo isolation/escaping/review rules (11),
host guard, audit chain, container/CI/compose configuration (17+). Equivalent mutants are noted (e.g. the explicit sequence check after the sequence number was bound into the hash).

## 5. What would make the evaluation credible
Blind cases written by domain experts from real (permitted) policy language; multiple annotators with agreement statistics; larger and noisier corpora; adversarial red-teaming by someone who
knows the tripwire; a reviewer study for automation bias; separate calibration/validation/test splits frozen by a third party.
</content>
