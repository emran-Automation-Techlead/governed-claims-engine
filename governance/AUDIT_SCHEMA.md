# Audit schema

Source of truth: `claims_engine/schemas.py` (`AuditRecord`, `RetrievalConfigRecord`, `HumanReview`), `review.py`, `audit_chain.py`.
**Design rule: identifiers, hashes, flags and timings - never the question text or policy text.**

## 1. Assessment event (`"event": "assessment"`)
| Field | Type | Meaning / privacy note |
|---|---|---|
| `trace_id` | string (uuid4 hex) | unique per request |
| `timestamp` | UTC datetime | record creation |
| `doc_ids`, `doc_sha256s` | lists | selected documents (scope) and their SHA-256; document version is shown in the UI via the registry and in each citation |
| `query_sha256` | hex or null | SHA-256 of the raw question; allows matching without storing it (a hash of a short question can be brute-forced - do not treat as anonymous) |
| `retrieval` | object | `method`, `top_k`, `params` (RRF k/depth, BM25 params, config and corpus fingerprints, abstain-policy version, `tau_lex`, semantic on/off, embedding revision) |
| `retrieved_chunk_ids` | list | ids of non-quarantined, in-scope evidence considered (`<doc_id>:p<page>:<clause>`) |
| `model_version`, `prompt_version` | string | `rules-1.0.0`, `n/a-deterministic` |
| `outcome` | enum | `potentially_covered` / `potentially_excluded` / `insufficient_evidence` / `human_review_required`; null if rejected |
| `escalation_reason` | string or null | policy-controlled template text (may name clause ids and pages), never user text |
| `latency_ms`, `prompt_tokens`, `completion_tokens` | numbers/null | tokens always null (no language model) |
| `error_category` | enum | `none`, `validation`, `ingestion`, `retrieval`, `guardrail`, `model`, `internal` |
| `node_path` | list | workflow nodes visited (shows retries, abstentions, rejections) |
| `guardrail_flags` | list | e.g. `query:override_instructions_en`, `evidence:role_marker`, `scope_violation`, `citation_validation_failed` |

Quarantined chunk ids are available in the workflow result and the demo's audit view, not in the stored `AuditRecord`.

## 2. Human-review event (`"event": "human_review"`)
`trace_id`, `reviewer_id` (pseudonym: letters, digits, space, `. _ -`; no `@`), `action` (`approve` | `override`), `override_status`,
`reason` (**free text typed by a human - may contain personal data; UI warns against it**), `proposed_status`, `timestamp`.
The original assessment is never modified: the effective status after review is derived (`proposed` / `override_status`).
A rejected request has no assessment and cannot be reviewed.

## 3. Optional tamper-evident log (`--audit-log FILE --tamper-evident`)
One JSON object per line: `{"seq": n, "prev": <hash of previous line, 64 zeros for the first>, "event": {...}, "hash": SHA-256("n|prev|canonical(event)")}`.
`python -m claims_engine.audit_chain verify FILE` returns OK/BROKEN. Detects edited events, forged `prev`/`seq`, deleted/reordered middle lines, malformed lines.
**Cannot detect** tail truncation or a wholesale forged chain without an externally stored head hash; no confidentiality; a malicious writer can append false events.

## 4. Retention and access (not implemented)
Default demo state is in memory only (200 runs). File logs have no rotation, retention limit, access control or encryption. A real deployment needs a
retention schedule, role-based access, encryption at rest, external anchoring and deletion procedures defined with the data-protection assessment.
</content>
