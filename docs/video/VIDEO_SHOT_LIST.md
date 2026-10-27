# Shot list

Every shot names the exact screen, command or file. All must be captured from the real repo and app. Recording hygiene: hide or crop
window titles and paths (no user-profile path visible), use a pseudonymous reviewer id (e.g. `rev-demo-01`), synthetic questions only.
Status is TODO unless the source already exists.

| Shot | Ch | Screen / command / file | What it must show | Status |
|---|---|---|---|---|
| S01 | 1 | `README.md`, top section in editor | Synthetic / decision-support wording | TODO |
| S02 | 1 | Title card (text only) | Video title | TODO |
| S03 | 2 | `Get-ChildItem data -Recurse` | 8 synthetic PDFs under policies, heldout, adversarial (EN/FR/DE) | TODO |
| S04 | 2 | `docs/WORKFLOW.mmd` rendered | Graph nodes | TODO (needs render) |
| S05 | 3 | `python -m pytest tests/test_ingestion.py -q` and `src/claims_engine/ingestion.py` | Checks and passing output | TODO |
| S06 | 3 | `src/claims_engine/chunking.py` plus one printed chunk | doc id, SHA-256, page, clause fields | TODO |
| S07 | 4 | `src/claims_engine/bm25.py`, `retrieval.py` (RRF k=60) | Code excerpt | TODO |
| S08 | 4 | Per-category retrieval benchmark from `eval/` (run `python -m claims_engine.eval_retrieval --no-semantic` or show the committed results) | "n=49, synthetic" caveat on screen | TODO |
| S09 | 5 | `src/claims_engine/workflow.py` node list | Node order | TODO |
| S10 | 6 | `docs/screenshot_1_supported_assessment.jpg` | Supported card with citation | READY |
| S11 | 6 | `python -m claims_engine.app` (lexical-only): one answerable question, one off-topic | Insufficient-evidence card | TODO |
| S12 | 7 | `src/claims_engine/citations.py`; `python -m pytest tests/test_citations.py -q` | Per-field checks passing | TODO |
| S13 | 8 | `docs/screenshot_2_review_override.jpg`, then a live override with reason | Original preserved | READY / TODO |
| S14 | 8 | `docs/screenshot_3_audit_viewer.jpg` | Audit record (ids and hashes only) | READY |
| S15 | 9 | `governance/EVALUATION_PROTOCOL.md` and `eval/` results: held-out 0.855/0.891, unsupported 0.000/0.018, coverage 0.575/0.725 | "Self-authored, not blind" | TODO |
| S16 | 9 | `python -m pytest -q` | Final line (588 passed with the local model present; 585 passed + 3 skipped without it; re-run when recording) | TODO |
| S17 | 10 | `governance/GRADIO_SECURITY_REVIEW.md` status table; `governance/PILLOW_ADVISORY_REVIEW.md` header | OPEN / DOCUMENTED items; 37 advisories | TODO |
| S18 | 10 | `python scripts/check_audit_allowlist.py <pip-audit.json> governance/accepted_advisories.json` (needs a fresh `pip-audit --format json` output first); `curl -X POST http://127.0.0.1:7860/gradio_api/upload` | Gate passing; 404 | TODO |
| S19 | 11 | Docker run with `--read-only --cap-drop ALL`, `docker exec ... id` (uid 10001), `/healthz`, headers, upload 404 | Real output, re-run while recording | TODO |
| S20 | 11 | `docs/AWS_DEPLOYMENT_PLAN.md` with a large label PROPOSED - NOT DEPLOYED | Plan only | TODO |
| S21 | 12 | Repo tree or the (private) GitHub repo page | Closing | TODO |

Do not shoot: AWS console, Cost Explorer, live-model output, or anything implying a deployed endpoint.
