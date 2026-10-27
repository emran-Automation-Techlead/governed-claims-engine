# Pre-registration (written 2026-10-27, BEFORE any M3 threshold was chosen or any held-out case was run)

Frozen inputs (SHA-256 recorded in `eval/m3/INPUT_HASHES.txt` when the run is produced):
`eval/calibration_cases.jsonl`, `eval/heldout_cases.jsonl`, `eval/adversarial_cases.jsonl`, `data/**`.
The M1/M2 baseline in `eval/baseline_m2/` is read-only and checked by a test.

## Honest framing
Policies, queries, labels, the cue lexicon and the stopword lists were all written by the same author
(the assistant) in one session. "Held-out" therefore means "not used to choose thresholds or variants",
NOT "blind". Differences of a few cases are not significant. Nothing here is evidence about real claims.

## Decision rules (fixed in advance; applied once; no re-tuning after viewing held-out results)
1. **Abstention threshold (tau_lex, tau_sem)**: swept on `calibration_cases.jsonl` only.
   Choose the smallest grid value with ZERO false accepts on the calibration unanswerable cases, then add
   one grid step as a safety margin (prefer abstention). With n unanswerable cases and 0 false accepts the
   95 % upper bound on the false-accept rate is about 3/n (rule of three) - reported, not hidden.
2. **Stopwords**: adopt iff (a) hit@5 on [M2 cases + held-out retrieval] does not drop and (b) fewer
   spurious results on unanswerable cases. Lists are fixed closed-class lists; no list edits after results.
3. **Subword (5-gram) matching for long tokens**: adopt only if it improves hit@5 on the German-compound
   held-out subset AND does not reduce hit@5 on the other held-out/M2 cases. Otherwise it stays OFF.
   The compound subset is small (7 cases) - a win there is weak evidence either way.
4. **Hybrid failures from M2 (Q18 "slow drip", Q47 "deductible")**: no synonym glossary and no RRF
   re-tuning to fix them; they are vocabulary gaps. Measure instead whether the system now abstains or
   escalates (safe failure) rather than emitting a wrong verdict.
5. **Assessor rules/cues are frozen** before the held-out run. Bugs found afterwards are reported as
   post-hoc fixes and the affected cases are flagged as no longer held-out.
## Amendments (logged, not silent)
- 2026-10-27: adversarial case ADV14 reworded ("Leerstand Diebstahlschutz ruht" -> "Gilt der Diebstahlschutz bei Leerstand")
  because the query duplicated a calibration query verbatim (found by `test_query_sets_do_not_overlap...`).
  The adversarial set had not been used to choose any threshold, variant or rule. Outcome re-checked after the change.
- 2026-10-27: POST-HOC assessor fix after the first held-out run: the cue `uebernehmen` never matched because
  accent folding turns "ü" into "u" (not "ue"). Fixed to `ue?bernehmen`. Affected cases: HO18 (both modes) and HO21
  (semantic mode) - these are no longer held-out. First-run outputs are kept in `eval/m3/*_run1_prefix.*`.
- 2026-10-27: while normalising line endings the frozen `eval/baseline_m2/RETRIEVAL_REPORT.md` bytes changed
  (CRLF->LF, content identical). Detected by `tests/test_baseline_frozen.py`, restored byte-exact (verified against
  the recorded SHA-256) and protected with `.gitattributes`.