# Abstention calibration (generated)

- Cases: 64 (36 answerable, 28 unanswerable), 4 synthetic policies.
- Chosen: **tau_lex = 0.5** (zero-false-accept value 0.45 + 1 step), **tau_sem = 0.66** (zero-false-accept value 0.64 + 1 step; null = semantic evidence not accepted).
- Rule-of-three 95 % upper bound on the false-accept rate with 0 observed in 28: ~11%. Do not read this as a measured safety level.

## Lexical gate sweep (BM25 top-3)

| tau_lex | answer rate | answered-wrong-only | false accepts |
|---|---|---|---|
| 0.05 | 0.944 | 2 | 7/28 |
| 0.1 | 0.944 | 2 | 7/28 |
| 0.15 | 0.944 | 2 | 7/28 |
| 0.2 | 0.944 | 1 | 7/28 |
| 0.25 | 0.944 | 1 | 6/28 |
| 0.3 | 0.944 | 1 | 3/28 |
| 0.35 | 0.944 | 1 | 3/28 |
| 0.4 | 0.889 | 0 | 2/28 |
| 0.45 | 0.861 | 0 | 0/28 |
| 0.5 **<- chosen** | 0.833 | 0 | 0/28 |
| 0.55 | 0.806 | 0 | 0/28 |
| 0.6 | 0.750 | 0 | 0/28 |
| 0.65 | 0.722 | 0 | 0/28 |
| 0.7 | 0.639 | 0 | 0/28 |
| 0.75 | 0.472 | 0 | 0/28 |
| 0.8 | 0.389 | 0 | 0/28 |
| 0.85 | 0.389 | 0 | 0/28 |
| 0.9 | 0.389 | 0 | 0/28 |
| 0.95 | 0.389 | 0 | 0/28 |
| 1.0 | 0.389 | 0 | 0/28 |

## Semantic gate sweep (hybrid top-3, tau_lex fixed at 0.5)

| tau_sem | answer rate | answered-wrong-only | false accepts |
|---|---|---|---|
| 0.1 | 1.000 | 0 | 25/28 |
| 0.12 | 1.000 | 0 | 24/28 |
| 0.14 | 1.000 | 0 | 22/28 |
| 0.16 | 1.000 | 0 | 21/28 |
| 0.18 | 1.000 | 0 | 21/28 |
| 0.2 | 1.000 | 0 | 19/28 |
| 0.22 | 1.000 | 0 | 17/28 |
| 0.24 | 1.000 | 0 | 13/28 |
| 0.26 | 1.000 | 0 | 12/28 |
| 0.28 | 1.000 | 0 | 12/28 |
| 0.3 | 1.000 | 0 | 10/28 |
| 0.32 | 1.000 | 0 | 9/28 |
| 0.34 | 1.000 | 0 | 9/28 |
| 0.36 | 1.000 | 0 | 6/28 |
| 0.38 | 1.000 | 0 | 5/28 |
| 0.4 | 0.972 | 0 | 5/28 |
| 0.42 | 0.972 | 0 | 5/28 |
| 0.44 | 0.944 | 0 | 4/28 |
| 0.46 | 0.944 | 0 | 3/28 |
| 0.48 | 0.944 | 0 | 3/28 |
| 0.5 | 0.944 | 0 | 3/28 |
| 0.52 | 0.944 | 0 | 3/28 |
| 0.54 | 0.944 | 0 | 3/28 |
| 0.56 | 0.944 | 0 | 2/28 |
| 0.58 | 0.944 | 0 | 1/28 |
| 0.6 | 0.917 | 1 | 1/28 |
| 0.62 | 0.917 | 1 | 1/28 |
| 0.64 | 0.917 | 0 | 0/28 |
| 0.66 **<- chosen** | 0.917 | 0 | 0/28 |
| 0.68 | 0.889 | 0 | 0/28 |
| 0.7 | 0.889 | 0 | 0/28 |
| 0.72 | 0.861 | 0 | 0/28 |
| 0.74 | 0.833 | 0 | 0/28 |
| 0.76 | 0.833 | 0 | 0/28 |
| 0.78 | 0.833 | 0 | 0/28 |
| 0.8 | 0.833 | 0 | 0/28 |
| 0.82 | 0.833 | 0 | 0/28 |
| 0.84 | 0.833 | 0 | 0/28 |
| 0.86 | 0.833 | 0 | 0/28 |
| 0.88 | 0.833 | 0 | 0/28 |
| 0.9 | 0.833 | 0 | 0/28 |

Lexical gate alone on hybrid top-3: answer rate 0.833, false accepts 0/28 []

## Chosen lexical threshold on the calibration set itself

answer rate 0.833; false accepts 0/28.
(This is the SAME data the threshold was fitted on - optimistic by construction. See the held-out report.)

## Limitations

- Few unanswerable cases; the zero-false-accept threshold is an upper-envelope of 28 queries, not a guarantee.
- Coverage is lexical: paraphrases and cross-lingual queries score ~0 and are abstained on in lexical-only mode (by design: prefer abstention).
- Calibrated on 4 short synthetic policies; thresholds will not transfer to long real policies without recalibration.
- The one-step margin is a judgment call, not a statistically derived guard band.
