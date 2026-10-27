# Narration generation plan (PREPARATION ONLY - nothing generated, no credits spent)

Prepared 2026-10-27. Generation is blocked until the user (a) confirms the credit balance, (b) confirms the applicable rate, (c) approves the final script, and (d) authorises generation.

## Verified by read-only calls
* Connector reachable (the voice listing and the model listing).
* Voice: **Martin - Calm, Clear Narrator**, id `akQnlreIUIoJxrTrosJj`, professional library voice, en-american, "low-pitched, calm, steady, informative"; listed under informative/educational use. (Preview not played.)
* Several text-to-speech models are available to this workspace; the workspace default is used unless the user chooses another.

## NOT verifiable (no supported read-only operation found)
* Remaining credit balance.
* Credits charged per character for any model/take.
* Whether the speech tool's default of two takes doubles the charge (the connector instructions say two takes by default; confirm).
* Whether the voice and model combination carries a different rate.
**The user must read the balance and the rate in the voice-service dashboard.** Do not infer sufficiency from the estimates below.

## Script size (measured from `VOICEOVER_SCRIPT.md`, 2026-10-27)
| Ch | Words | Characters | Est. seconds @145 wpm (estimate) | Planned file |
|---|---|---|---|---|
| C01 | 78 | 462 | 32 | `audio/C01_problem.mp3` |
| C02 | 90 | 556 | 37 | `audio/C02_architecture.mp3` |
| C03 | 73 | 430 | 30 | `audio/C03_ingestion.mp3` |
| C04 | 86 | 542 | 36 | `audio/C04_retrieval.mp3` |
| C05 | 92 | 595 | 38 | `audio/C05_workflow.mp3` |
| C06 | 87 | 549 | 36 | `audio/C06_outcomes.mp3` |
| C07 | 85 | 497 | 35 | `audio/C07_citations.mp3` |
| C08 | 75 | 472 | 31 | `audio/C08_review.mp3` |
| C09 | 166 | 1,068 | 69 | `audio/C09_evaluation.mp3` |
| C10 | 148 | 926 | 61 | `audio/C10_security.mp3` |
| C11 | 81 | 537 | 33 | `audio/C11_deployment.mp3` |
| C12 | 83 | 539 | 34 | `audio/C12_closing.mp3` |
| **Total** | **1,144** | **7,173** | **~7:55** | |

Counts are exact for the current script text (recount if it changes). If the rate were 1 credit per character (UNVERIFIED), one take of everything would be about 7,173 credits and the single-chapter test (C01) about 460. Those are illustrations, not quotes.

## Proposed procedure (after approval)
1. Single-chapter test: C01 only, **one take**, model chosen by the user (the default, or a cheaper one if the rate differs), stability/style left default. Listen, check pronunciation of: LangGraph, BM25, PyMuPDF, SHA-256, Pillow, Gradio, "RRF".
2. If accepted, generate C02-C12 one chapter per call, one take each, all on a single flow. Never repeat a call to retry a failure without asking.
3. After each file: record chapter id, flow/generation ids, model id, settings, characters submitted, duration measured with `ffprobe`, and SHA-256 of the file in `VIDEO_PRODUCTION_STATUS.md`. No secrets.
4. Measure real durations, then compute chapter timestamps and build the final `SUBTITLES.srt` (e.g. Whisper alignment or the script lines against measured chapter lengths). Label any remaining estimate.
5. Do not mark narration complete until all 12 files exist and have been listened to.

## Authorisation needed from the user
* Current credit balance and rate (from the dashboard).
* Model choice and number of takes (recommended: one).
* Go-ahead for the C01 test, then for the rest.
