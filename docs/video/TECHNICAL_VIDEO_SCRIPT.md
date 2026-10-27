# Technical video script - "Governed Claims Coverage Engine — Evidence-Grounded AI for Insurance"

Status: DRAFT 2026-10-27. Target length 6-8 min (estimate ~7.9 min of narration, 1,144 spoken words at ~145 wpm). No video or audio exists yet.
Narration text lives in `VOICEOVER_SCRIPT.md` (single source); screens and commands are in `VIDEO_SHOT_LIST.md`. Two cuts: full (12 chapters) and a 60-90 s portfolio cut.

## Accuracy rules for this video
* Show only real output: repo files, command runs, the working Gradio demo, the three screenshots in `docs/`.
* The assessor is deterministic and rule-based (`rules-1.0.0`), not an LLM. Data is synthetic. Not production-ready, not certified.
* Abstention and human review are safeguards, not proof of safety. The evaluation is self-authored and not blind.
* No claim of AI Act high-risk classification or DORA applicability (`governance/LEGAL_REFERENCES.md`: unresolved).
* Disclose: Pillow advisories (accepted, time-boxed to 2026-12-31), unauthenticated demo, in-memory review state, global audit tab.
* Label status on screen: IMPLEMENTED+TESTED / VERIFIED LOCALLY (Docker runtime image) / PROPOSED (AWS) / OUTSTANDING (image vulnerability scan; semantic image not in CI).
* No AWS console footage, no live-model responses, no dashboards that do not exist.

## Chapter outline (full cut)
| # | Chapter | On-screen focus | Est. |
|---|---|---|---|
| 1 | Problem and intended use | README intro, synthetic / decision-support wording | 0:35 |
| 2 | Architecture and synthetic corpus | `data/` tree, WORKFLOW.mmd overview | 0:40 |
| 3 | Ingestion, hashes, chunking | `ingestion.py`, `chunking.py`, hash/page/clause output | 0:35 |
| 4 | BM25 / semantic / hybrid RRF | `bm25.py`, `retrieval.py`, benchmark table (caveated) | 0:45 |
| 5 | LangGraph workflow | `docs/WORKFLOW.mmd` rendered, `workflow.py` node list | 0:40 |
| 6 | Supported / insufficient / rejected / review | demo screenshots + live demo questions | 0:45 |
| 7 | Citation integrity | `citations.py`, test run, mutation catch | 0:35 |
| 8 | Reviewer approve/override | demo review tab, audit viewer | 0:40 |
| 9 | Evaluation and limits | `eval/` results, protocol, "not blind" | 0:50 |
| 10 | Security, dependencies, limitations | governance docs, allowlist gate, upload 404 | 0:50 |
| 11 | Deployment: verified vs proposed | Docker evidence; AWS plan labelled PROPOSED | 0:40 |
| 12 | Closing | repo tree, summary | 0:25 |

## Portfolio cut (60-90 s) outline
1. 0:00-0:10 Title + "synthetic, decision support, rule-based" (C01).
2. 0:10-0:30 Demo: a question gives a supported assessment with citation; then a question that abstains (C06, C07).
3. 0:30-0:45 Reviewer override with reason; original preserved (C08).
4. 0:45-1:05 Evaluation honesty: numbers plus "self-authored, not blind" (C09).
5. 1:05-1:20 Limits: no auth, Pillow accepted risk, local-only (C10).
6. 1:20-1:30 Closing line (C12).

