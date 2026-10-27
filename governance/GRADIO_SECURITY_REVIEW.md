# Gradio demo: security review (Milestone 5)

Reviewed 2026-10-27 against Gradio 6.30.0 as served by `claims_engine.app`. Scope: the local demo and its container
configuration. **Nothing here is a penetration test or a certification.** Status vocabulary:

* **FIXED+TESTED** - implemented in this repo and covered by an automated test (and mutation-checked).
* **DOCUMENTED** - a limitation that remains; the recommended production control is described, not built.
* **OPEN** - known gap with no control in place.

## 1. Content Security Policy

**Current header** (`app.CSP`, sent on every response):
`default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:; media-src 'self' data: blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`

| Finding | Evidence | Status |
|---|---|---|
| `'unsafe-eval'` is **required** by Gradio 6.x `gr.HTML`. | Experiment 2026-10-27 in Chrome with `'unsafe-eval'` removed: every `gr.HTML` panel rendered "Error rendering HTML ... violates the following Content Security Policy directive because 'unsafe-eval' is not an allowed source of script" (console `EvalError` from the template compiler `new Function`). The earlier M4 statement was an assumption; it is now evidenced. | DOCUMENTED |
| `'unsafe-inline'` for scripts is needed by Gradio's inline bootstrap (`window.gradio_config`). | Not removed in an experiment (expected to break the page); treat as unverified-but-likely. | DOCUMENTED |
| Consequence: CSP does **not** stop XSS if untrusted markup ever reaches the page. XSS protection rests on **HTML-escaping every untrusted string** (policy text, questions, reviewer text, reasons) and on never rendering quarantined passages. | `tests/test_demo_service.py::test_untrusted_text_is_html_escaped_everywhere`; mutation checks (unescaped quote / reviewer reason) are caught. | FIXED+TESTED (escaping), DOCUMENTED (CSP weakness) |
| Remaining directives are strict: no third-party script/style/font/image/connect hosts, no framing, no form posts elsewhere. Third-party tags Gradio ships in its page (Google Fonts preconnect, a cdnjs script) are stripped. | `test_live_page_is_local_only_hardened_and_makes_no_third_party_references`; browser network log: all requests to 127.0.0.1. | FIXED+TESTED |

**Recommended production controls:** replace `gr.HTML` panels with native components or serve the result panels from a purpose-built front end
that does not need `unsafe-eval`; terminate TLS and add HSTS at the reverse proxy; add `Cross-Origin-Opener-Policy`/`Cross-Origin-Resource-Policy`;
re-run this experiment after each Gradio upgrade.

## 2. Authentication and authorisation

| Finding | Status |
|---|---|
| **No authentication.** Anyone who can reach the port can use every function. Document scope and reviewer identity are self-asserted (the reviewer id is only syntax-checked). | OPEN |
| **Binding guard.** The server binds to 127.0.0.1; binding elsewhere (needed inside a container) is refused unless `CLAIMS_ALLOW_NONLOOPBACK=1` is set explicitly. The container publishes only to loopback (`-p 127.0.0.1:7860:7860`, compose). | FIXED+TESTED (`test_non_loopback_binding_is_refused_without_explicit_opt_in`, config tests) |
| **Audit tab is global across sessions.** It lists the 30 most recent traces of *all* sessions and shows their audit metadata and review reasons; `allow_custom_value` also accepts any pasted trace id. (Assessment evidence and review state *are* session-isolated: tested.) Acceptable for one operator on loopback; wrong for multi-user use. | DOCUMENTED (behaviour pinned by `test_audit_listing_is_global_across_sessions_documented_limitation`) |
| Trace ids are 128-bit random (`uuid4().hex`), so guessing is impractical, but they are not secrets once listed. | DOCUMENTED |
| Gradio's built-in `auth=` is HTTP-form basic authentication with static credentials: not suitable for production. | DOCUMENTED |

**Recommended production controls:** authenticate at an identity-aware reverse proxy (OIDC/SAML, MFA); map the authenticated subject to
(a) the set of documents they may query - enforced server-side, replacing the caller-asserted `doc_ids`, (b) a reviewer identity written into
the audit record, (c) ownership of traces so the audit tab shows only the user's own (or role-based) records; separate roles for *assessor*,
*reviewer* and *auditor*; rate limiting; CSRF/origin checks at the proxy.

## 3. In-memory state

| Finding | Status |
|---|---|
| All runs and reviews live in process memory (cap 200, oldest evicted), so they are **lost on restart**, not shared across replicas, and not recoverable. Review history exists only while the process lives unless an audit log file is enabled. | DOCUMENTED |
| Eviction can drop an assessment before a reviewer acts; there is no queue, locking or double-review rule beyond append-only history. | DOCUMENTED |
| Concurrent use is safe within one process (lock around the store; 20-thread test), and isolation between requests is tested. | FIXED+TESTED |

**Recommended production controls:** durable store with transactional writes (review decisions must be atomic with their audit entry), explicit
review states and assignment, retention/deletion schedule aligned with the data-protection assessment, backups and restore tests.

## 4. Audit-log integrity

| Finding | Status |
|---|---|
| Default `--audit-log` is plain JSON lines: anyone with file access can edit or delete lines undetected. | DOCUMENTED |
| **Opt-in tamper-evident mode** (`--audit-log F --tamper-evident`): SHA-256 hash chain over `seq | previous-hash | canonical event`; `python -m claims_engine.audit_chain verify F`. Tests show detection of edited events, forged `prev`/`seq`, deleted or reordered middle lines, garbage lines; the sink refuses to append to a broken chain; concurrent writers keep the chain valid. | FIXED+TESTED (within limits below) |
| **What the chain does not do** (pinned by `test_documented_limit_tail_truncation...`): it cannot detect truncation of the *end* of the log or replacement by a freshly forged valid chain unless the latest head hash was stored somewhere the attacker cannot write; a malicious writer can append false events; events are not encrypted. | OPEN |
| Audit content: ids, hashes, flags, timings, reviewer pseudonym and **free-text review reasons** (which a human might fill with personal data). The question text is never stored (SHA-256 only). | DOCUMENTED |

**Recommended production controls:** write audit events to an append-only, access-controlled store (object lock / WORM, or a ledger service)
under a dedicated write-only identity; periodically anchor the head hash externally (signed timestamp, separate account); synchronise clocks;
alert on verification failure; restrict and redact free-text review reasons; define retention.

## 5. Other findings from this review

| Finding | Status |
|---|---|
| `mount_gradio_app` defaults to `show_error=True`: unexpected exceptions would send their message text to the browser. Now disabled; a live-client test forces an internal exception and asserts that its text does not reach the client. | FIXED+TESTED |
| Gradio serves its own **component config and API schema** (`/config`, `/gradio_api/info`, `/openapi.json`, `/gradio_api/openapi.json`) regardless of FastAPI settings; Swagger/ReDoc UIs are off (404). The endpoints leak no local paths or user names (tested) but reveal document ids, filenames and the UI structure to anyone who can connect. | DOCUMENTED (put behind authentication) |
| **Unauthenticated file upload (new in the Pillow follow-up).** Gradio always exposes POST /gradio_api/upload (observed: HTTP 200) and stores the file in its temp directory even when no component uses uploads: any client could fill the disk, and it is the delivery route an image-based exploit would need. Now blocked together with the file-serving and icon routes (/gradio_api/file*, /file=, /pwa_icon*, /gradio_api/resource*); a unique-marker test verifies nothing reaches the cache (and that with the block disabled it does). | FIXED+TESTED |
| Health endpoint `/healthz` returns `{"status":"ok"}` only (no state, version or data). | FIXED+TESTED |
| Response headers: CSP, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`. | FIXED+TESTED |
| No file upload, no free-text path input: only bundled synthetic PDFs can be assessed, so the (untested) hostile-PDF ingestion path is not reachable from the UI. | FIXED by design |
| Request size and rate: question limited to 2,000 characters (UI and workflow); request bodies are otherwise not size-limited by the app; Gradio queue concurrency is capped at 4; no rate limiting or lockout. | OPEN |
| Dependency advisories: Gradio 6.10.0 had three and Starlette 0.52.1 five; both fixed by upgrading to Gradio 6.30.0 / Starlette 1.10.0. **Pillow 12.3.0 has 37 advisories fixed only in 13.0.0, which Gradio 6.30.0's metadata still excludes (`pillow<13`).** All concern image-format parsing/saving; project code never imports PIL, the UI has no image/file components and nothing is uploaded, so exposure is low but not zero. See `DEPENDENCY_REPORT.md`. | DOCUMENTED (accepted risk) |
| Telemetry: Gradio analytics disabled; Hugging Face offline flags set; LangChain tracing forced off; the page makes no third-party requests (browser-verified). | FIXED+TESTED |

## 6. Verdict

Appropriate for **local, single-operator, synthetic-data demonstration only**. Before any shared or real-data use at minimum: authentication and
authorisation, durable and access-controlled audit storage with external anchoring, removal of `unsafe-eval` dependence (or an
accepted-risk decision), per-user trace ownership, rate limiting, a Pillow fix (or confirmation that the component is not reachable), and an
independent security test.
</content>
