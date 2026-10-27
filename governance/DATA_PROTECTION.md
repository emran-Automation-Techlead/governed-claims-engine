# Data protection (GDPR lens)

**Not legal advice; no GDPR-compliance claim.** Article references are from background knowledge (V3 in `LEGAL_REFERENCES.md`) except Art 22 (V2).
Controller/processor roles, lawful bases and national rules (Luxembourg: CNPD) were **not analysed**.

## 1. What the demo processes
| Data | Where | Personal data? |
|---|---|---|
| Eight fictional policy PDFs | bundled in `data/` | No (synthetic) |
| Questions typed into the UI | memory during the request; **only a SHA-256 is kept** | Should be none (UI says "do not enter real personal data"), cannot be enforced |
| Reviewer id | audit/review record | Pseudonym required (letters/digits/space/`._-`, no `@`) |
| Review explanation (free text) | review record, optional log file | **Could contain personal data if a user types it**; UI warns |
| Trace ids, document hashes, flags, timings | audit record | No |
| Embedding model (optional) | local folder | not personal data; its training data was not assessed |
No telemetry, no cookies set by the app, no third-party requests (browser-verified), no cloud transfer (offline), no cross-border transfer by design.

## 2. If real claims data were ever used (not done, not authorised here)
| Topic | Consideration | Status in this repo |
|---|---|---|
| Art 5 principles | purpose limitation, minimisation, accuracy, storage limitation, integrity | Minimisation by design (no question text stored); the rest undefined |
| Art 6 / Art 9 | lawful basis; health data is a special category | not analysed |
| Art 22 | decisions *solely* automated with legal or similarly significant effects are restricted; safeguards include human intervention, expressing a view, contesting | Design keeps a person in the loop (mandatory review for non-verdicts). Whether a review is *meaningful* depends on process, authority, training and automation-bias controls - **not evaluated** |
| Art 15 / 13-14 | information about the logic involved | Audit records and cited clauses give a basis; no data-subject-facing tooling |
| Art 25 | data protection by design and default | partly: scope enforcement, no stored text, pseudonymous reviewers |
| Art 28 | processors | none today; a hosted deployment would create one |
| Art 30 | records of processing | not maintained |
| Art 32 | security | see `GRADIO_SECURITY_REVIEW.md` (no authentication, no encryption at rest) |
| Art 33-34 | breach notification | no process |
| Art 35 | DPIA | **Would almost certainly be needed** before processing real claims at scale with automated support; not performed |
| Chapter V | transfers | none (offline); a cloud deployment would need a transfer analysis |
| Data-subject rights (access, rectification, erasure) | | no tooling; in-memory state limits retention but is not a deletion mechanism |

## 3. Practical rules for anyone running the demo
Use only the bundled synthetic documents; do not type real names, policy numbers or health details into the question or explanation boxes;
use pseudonymous reviewer ids; treat any enabled audit log as potentially containing whatever reviewers typed.
</content>
