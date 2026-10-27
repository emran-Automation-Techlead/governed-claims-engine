# Workflow evaluation (generated; measured numbers only)

- Abstain policy `cal-2026-10-27-v1`: tau_lex=0.5, tau_sem=0.66. zero-false-accept threshold(s): lex=0.45, sem=0.64; +1 grid step margin; calibrated on 64 cases (28 unanswerable) over 4 synthetic policies; rule-of-three 95% upper bound on false-accept rate ~0.11
- Held-out = not used to choose thresholds/variants. NOT blind: same author wrote policies, cases, cues. See eval/PREREGISTRATION.md.
- Assessor: deterministic rules, offline, $0. No LLM involved anywhere.

## lexical-only - heldout (n=55)

- status accuracy (== primary label): 0.618; acceptable-status rate: 0.855
- verdicts emitted: 0.436; coverage on cases whose label is a verdict: 0.575
- **unsupported verdict rate: 0.000** []; wrong-direction verdicts: 0 []
- abstention quality (expected-abstain cases handled acceptably): 0.867 (n=15); over-abstention on verdict cases: 0.150
- independent citation re-validation failures: 0; cross-document leaks: 0; query text found in audit record: 0
- mean latency: 4.8 ms; estimated cost per assessment: $0 (no paid calls)

| category | n | acceptable | verdict coverage | unsupported | abstention quality |
|---|---|---|---|---|---|
| clear | 20 | 0.950 | 0.950 | 0.000 | - |
| cross_lingual | 7 | 1.000 | 0.000 | 0.000 | - |
| german_compound | 7 | 0.429 | 0.333 | 0.000 | 1.000 |
| misleading_or_conflicting | 7 | 0.714 | 1.000 | 0.000 | 0.600 |
| paraphrase | 6 | 0.833 | 0.000 | 0.000 | 1.000 |
| unanswerable | 8 | 1.000 | - | 0.000 | 1.000 |

## lexical-only - adversarial (n=19)

- status accuracy (== primary label): 1.000; acceptable-status rate: 1.000
- verdicts emitted: 0.158; coverage on cases whose label is a verdict: 1.000
- **unsupported verdict rate: 0.000** []; wrong-direction verdicts: 0 []
- abstention quality (expected-abstain cases handled acceptably): 1.000 (n=16); over-abstention on verdict cases: 0.000
- independent citation re-validation failures: 0; cross-document leaks: 0; query text found in audit record: 0
- mean latency: 3.8 ms; estimated cost per assessment: $0 (no paid calls)

| category | n | acceptable | verdict coverage | unsupported | abstention quality |
|---|---|---|---|---|---|
| cross_document | 5 | 1.000 | - | 0.000 | 1.000 |
| injection_bypass | 2 | 1.000 | - | 0.000 | 1.000 |
| poisoned_document | 5 | 1.000 | 1.000 | 0.000 | 1.000 |
| query_injection | 7 | 1.000 | - | 0.000 | 1.000 |

### lexical-only: injection screen on adversarial cases that expect a flag: 8/8 flagged

Paraphrased injections the keyword screen did NOT flag: 2/2; outcomes: ['insufficient_evidence', 'insufficient_evidence'] (no verdict was emitted: the assessor is deterministic and ignores instructions).

### lexical-only: the 52 M2 cases through the full workflow (system-level view)

- answerable (49): verdict with only relevant citations 18; verdict with an off-target citation 0 []; abstained/escalated 31
- unanswerable (3): given a verdict 0; abstained 3
- deterministic re-run identical: True

M2 failure review (Q18/Q47 = hybrid failures; Q50-52 = unanswerable): Q18: insufficient_evidence cited=[]; Q47: insufficient_evidence cited=[]; Q50: insufficient_evidence cited=[]; Q51: insufficient_evidence cited=[]; Q52: insufficient_evidence cited=[]

## semantic (hybrid) - heldout (n=55)

- status accuracy (== primary label): 0.727; acceptable-status rate: 0.891
- verdicts emitted: 0.582; coverage on cases whose label is a verdict: 0.725
- **unsupported verdict rate: 0.018** ['HO25']; wrong-direction verdicts: 0 []
- abstention quality (expected-abstain cases handled acceptably): 0.867 (n=15); over-abstention on verdict cases: 0.100
- independent citation re-validation failures: 0; cross-document leaks: 0; query text found in audit record: 0
- mean latency: 49.8 ms; estimated cost per assessment: $0 (no paid calls)

| category | n | acceptable | verdict coverage | unsupported | abstention quality |
|---|---|---|---|---|---|
| clear | 20 | 0.950 | 0.950 | 0.000 | - |
| cross_lingual | 7 | 0.857 | 0.429 | 0.000 | - |
| german_compound | 7 | 0.714 | 0.667 | 0.143 | 0.000 |
| misleading_or_conflicting | 7 | 0.857 | 1.000 | 0.000 | 0.800 |
| paraphrase | 6 | 0.833 | 0.200 | 0.000 | 1.000 |
| unanswerable | 8 | 1.000 | - | 0.000 | 1.000 |

## semantic (hybrid) - adversarial (n=19)

- status accuracy (== primary label): 1.000; acceptable-status rate: 1.000
- verdicts emitted: 0.158; coverage on cases whose label is a verdict: 1.000
- **unsupported verdict rate: 0.000** []; wrong-direction verdicts: 0 []
- abstention quality (expected-abstain cases handled acceptably): 1.000 (n=16); over-abstention on verdict cases: 0.000
- independent citation re-validation failures: 0; cross-document leaks: 0; query text found in audit record: 0
- mean latency: 41.4 ms; estimated cost per assessment: $0 (no paid calls)

| category | n | acceptable | verdict coverage | unsupported | abstention quality |
|---|---|---|---|---|---|
| cross_document | 5 | 1.000 | - | 0.000 | 1.000 |
| injection_bypass | 2 | 1.000 | - | 0.000 | 1.000 |
| poisoned_document | 5 | 1.000 | 1.000 | 0.000 | 1.000 |
| query_injection | 7 | 1.000 | - | 0.000 | 1.000 |

### semantic (hybrid): injection screen on adversarial cases that expect a flag: 8/8 flagged

Paraphrased injections the keyword screen did NOT flag: 2/2; outcomes: ['insufficient_evidence', 'insufficient_evidence'] (no verdict was emitted: the assessor is deterministic and ignores instructions).

### semantic (hybrid): the 52 M2 cases through the full workflow (system-level view)

- answerable (49): verdict with only relevant citations 18; verdict with an off-target citation 1 ['Q37']; abstained/escalated 30
- unanswerable (3): given a verdict 0; abstained 3
- deterministic re-run identical: True

M2 failure review (Q18/Q47 = hybrid failures; Q50-52 = unanswerable): Q18: insufficient_evidence cited=[]; Q47: insufficient_evidence cited=[]; Q50: insufficient_evidence cited=[]; Q51: insufficient_evidence cited=[]; Q52: insufficient_evidence cited=[]

