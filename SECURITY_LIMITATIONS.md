# Security design and known limitations (Milestone 3)

Status: prototype on synthetic data. This is an engineering description, not a certification, a
penetration-test result, or a legal/compliance statement. Written 2026-10-27.

## What protects what

| Threat | Control | Where | Strength / honest caveat |
|---|---|---|---|
| Policy text carrying instructions ("ignore previous instructions...") | **Architecture:** policy text is data. The assessor is deterministic code that classifies clauses with fixed cue patterns; it has no prompt, no tools, and cannot "follow" text. Injected steering words inside a clause do not change its classification (tested). | `assessor.py` | Strong **for this assessor**. This guarantee does not carry over to an LLM assessor. |
| Same, as a tripwire | Regex/keyword screen on the request and on every retrieved chunk; hits are quarantined and force mandatory human review. | `guardrails.py` | **Weak, bypassable.** Paraphrase, typos, other languages, split lines, encodings all evade it (two paraphrased attacks in the adversarial set are not flagged; tests assert this openly). It is a tripwire, not a boundary. |
| Fabricated or mismatched citations | Every cited reference must match a chunk retrieved in *this* request: chunk id, doc id, SHA-256, version, page, clause id, verbatim quote, in-scope document, registry entry. Failures retry once, then abstain. | `citations.py`, `workflow.py` | Strong against fabrication of *references*. It does not prove the cited clause *supports* the verdict; that is the assessor's job and a human's check. |
| Cross-document leakage | Default-deny scope: request must list document ids; retrieval filters by id; a second check drops (and flags, and fails closed on) any out-of-scope hit; citations re-check scope. Negative tests cover 42 ordered document pairs with verbatim "lure" text. | `retrieval.py`, `workflow.py`, `citations.py` | Enforced inside one process on one index. There is **no authentication or per-user authorisation** yet: the caller is trusted to state which documents it may see. |
| Over-confident verdicts | Calibrated abstention gate (fails closed if uncalibrated), conflict/exception/neutral-clause escalation, mandatory review for every non-verdict or flagged result. | `support.py`, `assessor.py` | Calibrated on 64 synthetic cases; see below. |
| Sensitive data in logs | Audit records hold ids, hashes, flags, timings; never the query or policy text. Rejection reasons name fields, never echo input. | `schemas.AuditRecord`, `workflow.py` | Human reviewers' free-text `reason` *is* stored in the review event; treat it as sensitive. No PII detection/redaction exists. |
| Hostile uploads (HTTP) | Gradio's upload/file-serving routes (always on by default) are blocked at the server wrapper; the UI has no file or image components (tested). | `app.BLOCKED_PATH_PREFIXES` | Fixed in M5 follow-up; see `governance/PILLOW_ADVISORY_REVIEW.md`. |
| Hostile uploads (ingestion) | Type/magic/size/page limits, encrypted-PDF rejection, text-only extraction (nothing rendered or executed). | `ingestion.py` | Not tested against malicious PDFs (JavaScript, embedded files, parser exploits in PyMuPDF). Run ingestion in a sandbox before any real use. |
| Network exfiltration / telemetry | No node makes network calls (a test blocks sockets during runs); LangChain/LangSmith tracing env vars forced off. | `workflow.py` | The semantic model is loaded offline from a checksum-verified local folder. Supply-chain risk of the Python wheels is unmitigated (versions pinned, hashes not). |

## What keyword screening does and does not do

It flags obvious EN/FR/DE instruction-like phrases, role markers, chat-template tokens, markup, hidden
Unicode and long encoded blobs. It produced **no false positives** on the 87 genuine synthetic chunks and
flagged exactly the 2 deliberately poisoned clauses (of the 8 chunks in that document). That says nothing about real documents or real attackers.
**Do not describe this system as protected against prompt injection.** The honest statement is: the current
deterministic assessor is not steerable by text; the screen is an additional alarm; if an LLM is introduced,
injection becomes a first-class risk again and needs its own design (delimited data, no tools, output
validation, red-teaming).

## Abstention policy (explicit)

* A retrieved chunk is "supported" if IDF-weighted lexical coverage of the query >= `tau_lex`, or (semantic mode)
  cosine >= `tau_sem`. Thresholds live in `calibration/abstain_policy.json`; if absent, the policy **fails closed**.
* `tau_lex = 0.5`, `tau_sem = 0.66`: smallest value with zero false accepts on the 28 unanswerable calibration
  cases, plus one grid step (judgment, not statistics). With 0/28 observed, the 95 % upper bound on the false-accept
  rate is about 11 % (rule of three). **No safety level is claimed.**
* The semantic threshold is steep: two grid steps lower (0.62) already admitted one unanswerable query on the
  calibration set. A different embedding model or corpus needs recalibration.
* Consequences: in lexical-only mode paraphrases and cross-language questions are abstained on by design; this
  costs coverage (see the evaluation report) and buys fewer unsupported verdicts.

## Residual risks and gaps

1. No authentication/authorisation; scope is caller-asserted.
2. Cue lexicon is hand-written for EN/FR/DE phrasing in 7 short synthetic policies; real policy language will
   produce misclassifications. The assessor never claims understanding and escalates when unsure, but it can still
   emit a wrong *direction* on unseen wording.
3. Held-out data was authored by the same party as the rules (not blind), so measured rates are optimistic.
4. Review UI, role separation of reviewers, tamper-evident audit storage, retention and deletion are not built.
5. Ingestion of hostile PDFs untested; no antivirus/sandbox.
6. Dependency supply chain: pinned versions, no hash pinning, no SBOM/vulnerability scan run.
7. Nothing here addresses EU AI Act / GDPR / DORA obligations; that analysis is a separate, source-verified task.
