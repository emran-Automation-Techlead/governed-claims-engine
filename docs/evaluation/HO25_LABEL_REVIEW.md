# HO25 label review

**Status: OPEN - decision pending explicit approval.** Opened 2026-10-27. This document changes nothing: `eval/heldout_cases.jsonl`,
the frozen baseline, the calibration policy and every reported metric are untouched.

## 1. The case
| Field | Value |
|---|---|
| Case id | HO25 (`eval/heldout_cases.jsonl`, line 25; category `german_compound`; held-out set, n=55) |
| Document / scope | `synthetic_home_policy_de.pdf` |
| Query | `Wasserschaden` (one word, "water damage") |
| `relevant` | `synthetic_home_policy_de.pdf#1.2` |
| `primary` | `human_review_required` |
| `acceptable` | `human_review_required`, `insufficient_evidence` |

## 2. Observed behaviour (re-run 2026-10-27, identical to the committed run)
| Mode | Status | Cited | Counted as |
|---|---|---|---|
| lexical-only | `insufficient_evidence` (abstained; priority `mandatory` review) | none | acceptable |
| semantic (hybrid) | `potentially_covered` (priority `standard`) | `#2.2` | **unsupported verdict** (a verdict outside the acceptable set) |

This single case is the whole semantic unsupported-verdict rate: 1/55 = **0.018** (lexical 0.000). Citation validation passed (no errors, no
cross-document leak). `M3_FINDINGS.md` already notes the label "is arguably too strict" and says "labels were frozen before running, so the number stands".
(That file says clause 2.2 *water cover*; the clause is the pipe-burst clause quoted below.)

## 3. Evidence reviewed
* **Clause text** (German home policy, synthetic, read from the ingested PDF; encoding shown approximately because the terminal is not UTF-8):
  * 1.2 - "'Leitungswasserschaden' ist der plötzliche und unvorhergesehene Austritt von Wasser aus fest verlegten Rohren der versicherten Wohnung." (a definition)
  * 2.2 - "Leitungswasser. Wir ersetzen Schäden durch plötzlichen Rohrbruch, einschließlich der Kosten für die Suche nach der undichten Stelle." (coverage)
  * 3.1 - "Verschleiß. Nicht versichert sind normale Abnutzung, Rost, Schimmel und allmähliche Durchfeuchtung." (exclusion for gradual moisture)
  * The policy has no clause that defines or covers the word "Wasserschaden" itself.
* **Rubric** (`governance/EVALUATION_PROTOCOL.md`, `eval/PREREGISTRATION.md`): labels carry a `primary` status plus an `acceptable` set "to allow genuine
  ambiguity"; an *unsupported verdict* is "a verdict outside the acceptable set". Decision rule 5: assessor rules/cues are frozen before the held-out run;
  later bugs are post-hoc fixes with affected cases flagged. Authorship caveat: same author wrote policies, queries and labels; "held-out" is not "blind".
* **Comparable cases in the same set** (short keyword queries): HO13 `Auslandskrankenschutz Notfallbehandlung`, HO18 `Krankenrücktransport`, HO21 `Rücktransport Kosten`
  are labelled `potentially_covered` against a coverage clause; HO15, HO16, HO20, HO23 are labelled `potentially_excluded`. HO25 is the only
  short keyword query whose `relevant` clause is a *definition* and whose label is `human_review_required`.
* **Assessor behaviour** (`assessor.py` header): "only coverage clause(s) -> potentially_covered"; escalation applies when coverage and exclusion/conflict evidence both appear.
  "Only definitions / limits / procedures -> human_review" is the rule the label appears to anticipate: with 1.2 (a definition) as the only relevant clause, the expected outcome is
  human review. In the semantic run only clause 2.2 was cited, so the coverage-only rule fired instead.

## 4. Arguments for retaining the current label
1. The query names no event. Under this policy, "water damage" can be covered (sudden pipe burst, 2.2) or excluded (gradual moisture, 3.1) depending on facts the
   query lacks. The conservative expected outcome - human review or insufficient evidence - is defensible, and the system's `potentially_covered` omitted any
   hint of 3.1.
2. The semantic result carried `standard` review priority, not the `mandatory` priority the lexical run assigned, so the more permissive outcome also got lighter handling.
3. The label was written and frozen before the run; changing it after seeing that it costs the system a point is the textbook post-hoc adjustment the pre-registration forbids ("no re-tuning after viewing held-out results").
4. The project's stated stance prefers abstention to an under-specified verdict.

## 5. Arguments for changing it
1. Internal inconsistency: comparable keyword queries (HO13, HO18, HO21) are labelled `potentially_covered` when a coverage clause matches. Applied consistently,
   "Wasserschaden" -> the water coverage clause 2.2 would be an expected hit.
2. The `relevant` list names only the definition (1.2) and omits 2.2, which is the clause an informed reviewer would look at first. The cited clause is real,
   on topic and passed verbatim citation validation.
3. `potentially_covered` is a hedged, non-binding status shown with a "preliminary - not a claim decision" banner and a reviewer path.
4. The author already recorded the label as "arguably too strict" (`M3_FINDINGS.md` section 4; `EVALUATION_PROTOCOL.md`: "labels HO25 and Q37 are arguably too strict").

## 6. Recommended disposition
**Retain the label in the reported results; do not edit `heldout_cases.jsonl` in place.** Rationale: the arguments on both sides are real, which is exactly the
situation where an author changing the label after seeing the result is least trustworthy. The honest outcome is to keep the reported 0.018 together with the
disclosure that its single driver is a debatable label, which the video script already says.

If you want the question resolved properly, do it as a *versioned* change:
1. Create `eval/heldout_cases_v2.jsonl` (new file; v1 stays byte-identical and hash-recorded), with HO25 changed and the reason written in the file's header or a changelog.
   Ideally have a second reviewer who has not seen the outcome decide the label, and apply the same short-keyword rule to every comparable case.
2. Add a dated amendment to `eval/PREREGISTRATION.md` stating that this is a post-hoc label revision made after seeing results, and which cases are affected.
3. Report **both** sets side by side. Do not replace the old numbers.
4. The change would need a *disclosed metric recalculation*. Arithmetic illustration only (not a re-run): if `potentially_covered` were acceptable for HO25, the semantic
   unsupported-verdict rate would go 0.018 -> 0.000 and the semantic acceptable-status rate 0.891 (49/55) -> 0.909 (50/55); lexical numbers would be unchanged.
   The video and `VOICEOVER_CLAIM_CHECK.md` would have to be updated, and the improvement must not be presented as a system improvement.

**A label change therefore does require a separately versioned evaluation dataset and a disclosed recalculation; it must not be a silent edit.**

## 7. What was not done
* No label, case file, baseline, threshold or report was modified; no metric was recomputed under a changed label.
* No second reviewer was consulted; the author of the labels and this review is the same person, the project author, who wrote the policies.
* No decision has been made. **Pending your explicit approval** of one of: (A) retain as is (recommended); (B) open the versioned v2 process above; (C) other.
