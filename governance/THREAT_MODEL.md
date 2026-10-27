# Threat model (lightweight STRIDE) - demo and container

2026-10-27. Companion to `SECURITY_LIMITATIONS.md` (workflow/assessor view) and `GRADIO_SECURITY_REVIEW.md` (UI/server view).
Controls listed are *implemented*; "test" points to the automated evidence. Not a penetration test.

## Assets
Integrity of assessments and citations; confidentiality of document scope and (in real use) claims data; integrity/availability of the audit
trail; integrity of the pinned model and dependencies; the reputation risk of presenting a synthetic demo as a real system.

## Actors and trust boundaries
| Actor | Trust |
|---|---|
| Operator running the app locally | trusted |
| Browser user of the UI | **untrusted** (no authentication); input crosses boundary B1 |
| Policy PDFs / retrieved text | **untrusted data** (boundary B2: never interpreted as instructions) |
| PyPI / Hugging Face / Docker Hub | supply chain (boundary B3): pinned, hashed, verified, fetched only by explicit commands |
| Container runtime / host | trusted but constrained (non-root, read-only, no capabilities, loopback-published) |

## Threats and controls
| STRIDE | Threat | Control | Test / evidence | Residual |
|---|---|---|---|---|
| Spoofing | Pretend to be another reviewer or user | Reviewer id syntax check only | `test_reviewer_id_must_be_a_pseudonym` | **Open**: no authentication; ids are self-asserted |
| Tampering | Forge a citation or evidence to support a verdict | Citations must match this request's retrieved chunk on id, doc id, SHA-256, version, page, clause, verbatim quote, scope | `test_citations.py` (each field), workflow retry/abstain tests, mutation checks | Does not prove the cited clause *supports* the verdict |
| Tampering | Inject instructions via policy text or question | Deterministic assessor; tripwire; quarantine; mandatory review | `test_workflow.py`, `test_stopwords_guardrails.py`, poisoned-document tests | Tripwire bypassable; LLM would reintroduce risk |
| Tampering | Edit/delete audit lines | Optional SHA-256 hash chain, verifier CLI | `test_audit_chain.py` | Tail truncation / full forgery undetected without external anchor |
| Tampering | Swap the embedding model | Pinned revision + per-file SHA-256 manifest verified on every load; loaded offline | `test_embeddings.py` | Manifest itself is a local file |
| Tampering | Malicious/compromised dependency | Version + SHA-256 pins (container), `pip-audit` in CI, Dependabot | `test_container_requirements_are_fully_hash_pinned`, DEPENDENCY_REPORT | Hashes prove "what PyPI published", not "benign"; no SBOM |
| Repudiation | Reviewer denies an override | Review events recorded (reviewer id, action, reason, proposed vs effective, timestamp) | `test_reviewer_actions_are_written_to_the_audit_trail` | Identity unauthenticated; in-memory unless a log is enabled |
| Information disclosure | Cross-document evidence leak | Default-deny scope + three independent checks | 42-pair negative test; live two-session test | Scope claimed by caller |
| Information disclosure | Question text or personal data in logs | Question never stored; rejection reasons never echo input | `test_question_text_is_stored_nowhere` | Free-text review reasons stored |
| Information disclosure | Exception text / internals to browser | `show_error=False`; schema endpoints checked for path/user leakage | `test_unexpected_server_errors_do_not_leak_exception_text...` | `/config`, `/openapi.json` expose UI structure |
| Information disclosure | Third-party tracking / fonts / CDN | Tags stripped, strict CSP `connect-src 'self'`, analytics off | `test_live_page_is_local_only...`; real-browser network log | none known |
| Denial of service | Large/many requests, oversized input | 2,000-char limit, queue concurrency 4, pids/memory limits in compose | `test_assess_callback_survives_invalid_input` | **No rate limiting**, no body-size limit |
| Denial of service / Tampering | Upload files through Gradio's always-on upload endpoint (disk filling; delivery route for image exploits) | Upload, file-serving and icon routes blocked at the wrapper; UI has no file/image components (guard test) | `test_upload_and_file_serving_routes_are_blocked`, `test_blocked_uploads_leave_nothing_in_the_gradio_cache`, `test_ui_contains_no_component_...` | Other undiscovered Gradio routes; Pillow advisories accepted (`PILLOW_ADVISORY_REVIEW.md`) |
| Denial of service | Malicious PDF | No upload path in UI; ingestion limits (size, pages, encrypted, malformed) | `test_ingestion.py` | Ingestion of hostile PDFs not fuzzed; only bundled files reachable |
| Elevation of privilege | Container escape / privilege use | Non-root user, read-only root fs, `cap_drop: ALL`, `no-new-privileges`, no secrets, loopback publish | static config tests (`test_container_and_ci_config.py`) | Image built and smoke-tested locally 2026-10-27 (`docs/RELEASE_GATES.md`); **OS packages and Python wheels not vulnerability-scanned** |
| Elevation of privilege | CI compromise | Least-privilege token, SHA-pinned official actions, no secrets, no `pull_request_target`, no credential persistence | config tests | Workflow has run green on `main` (lexical target only); Dependabot PR branches show 4 failing docker-build jobs |
| (Integrity of claims) | Overstating assurance in reports/video | Pre-registration, frozen baseline, "not blind", limitations banners | `test_baseline_frozen.py`, M3 findings | Reader judgement |
</content>
