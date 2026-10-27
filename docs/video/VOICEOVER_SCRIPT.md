# VOICEOVER SCRIPT - Governed Claims Coverage Engine

Status: **DRAFT for user review. No audio generated.** Word counts are exact for this text; durations are *estimates* at about 145 words per minute.
Every statement maps to code, a test or a document in this repository. Read it as one calm, plain voice; no hype.

## [C01] Problem and intended use (~85 words)
This is the Governed Claims Coverage Engine: a prototype that helps a human reviewer check what an insurance policy says about a question. It is a decision-support tool, not a decision-maker. Everything you will see uses synthetic policies I generated myself. No real customers, no real claims. The goal is to show how an AI-assisted workflow can stay grounded in evidence, say "I don't know" when it should, and leave an audit trail that a reviewer can inspect.

## [C02] Architecture and synthetic corpus (~90 words)
There are eight synthetic policy documents, and one of them is a deliberately poisoned policy used for adversarial tests. The others are home, travel and motor policies in English, French and German. The pipeline reads the PDFs, splits them into clause-sized chunks, retrieves candidate passages, and passes them through a LangGraph workflow. An important point: the final assessment is produced by a deterministic rule engine, version rules one point zero. It is not a large language model, so it cannot be talked into a verdict by text inside a document.

## [C03] Ingestion, hashes and chunking (~85 words)
Ingestion uses PyMuPDF and checks file type, size, page count and encryption before reading anything. Each document gets a SHA-256 hash and a version, and each chunk keeps its page and clause identifier. Those fields matter later, because a citation will only be accepted if every one of them still matches. Chunks are clause-aware, one page at a time, so a citation points to something a person can actually find in the document.

## [C04] Retrieval: BM25, semantic, hybrid (~100 words)
Retrieval has two halves. A BM25 search that I wrote in-house handles exact terms and clause numbers, with accent folding for French and German. An optional multilingual embedding model handles meaning across languages. Reciprocal rank fusion combines them. In my benchmark, vector search alone missed exact clause identifiers, and keyword search alone missed cross-language questions. That is a result on a small, synthetic set, so I report it as a finding, not as proof that hybrid is always better. The demo you will see runs lexical-only.

## [C05] The LangGraph workflow (~90 words)
Each question moves through explicit steps: validate the input, screen the question, retrieve, enforce document scope, screen the evidence, score it, assess, validate the citations, then a human-review gate, and finally an audit record. Scope is default-deny: a question can only see documents it was explicitly allowed to see, and that is enforced three separate times: the search itself is filtered to the allowed documents, the results are re-checked afterwards, and the citation validator rejects anything out of scope. Anything that fails a check is rejected or abstains. It does not guess.

## [C06] Supported, insufficient, rejected, human review (~100 words)
The system has four kinds of outcome. Supported means a retrieved clause backs the answer. Insufficient evidence means retrieval did not find enough, so the system abstains. Rejected means the input or evidence failed a safety check. And human review is required whenever a clause contains an exception, a conflict, or an unclear condition. Abstaining and escalating are safeguards. They reduce risk, but they are not proof of safety. The abstention threshold was calibrated on a separate set of cases and then frozen before the held-out evaluation.

## [C07] Citation integrity (~85 words)
Before any answer is shown, every citation is validated against the passage that was actually retrieved for this request: chunk id, document id, SHA-256, version, page, clause, verbatim quote and scope. A fabricated or altered citation is caught and the workflow retries or abstains. There is a test that breaks each of those fields in turn, and every one is rejected. To be clear about the limit: a valid citation proves the quote is real. It does not prove the clause truly supports the verdict.

## [C08] Reviewer approve and override (~85 words)
The reviewer sees the preliminary assessment, the evidence, and what information is missing. They can approve it, or override it, and an override requires a written reason. The original machine assessment is never overwritten; the review is appended as a separate event with the reviewer's pseudonym, the action, and a timestamp. Questions are never stored, only a hash. The wording on screen is "preliminary, not a claim decision", because automation bias is a real risk.

## [C09] Evaluation, adversarial tests and limits (~110 words)
Evaluation used three sets: sixty-four calibration cases to set the abstention threshold, fifty-five held-out cases, and nineteen adversarial cases. The earlier retrieval baseline is kept frozen and checksummed. On the held-out set, the lexical and semantic variants reached acceptable-status rates of eighty-five point five and eighty-nine point one percent, with unsupported-verdict rates of zero and one point eight percent. That single unsupported verdict came from the semantic variant on a one-word German query, and its label is debatable; I have flagged it for a separate review rather than changing it. One post-hoc fix, for a German-character bug found after the first run, raised those rates from eighty-three point six and eighty-five point five percent; it is disclosed in the findings. The price is abstention: verdict coverage was fifty-seven point five and seventy-two point five percent. And the honest caveat: I wrote these cases myself, so this is not a blind evaluation. It shows the design works as intended, not that it would work on real claims.

## [C10] Security, dependencies, limitations (~110 words)
Security findings matter more than good numbers. The demo has no authentication, review state lives in memory, and the audit tab is visible across sessions, so it is local-only. The keyword injection screen can be bypassed, and the content security policy needs unsafe-eval because of Gradio. A dependency audit found thirty-seven Pillow advisories: four critical, twenty-two high and eleven moderate. All are fixed only in Pillow thirteen, which this Gradio version does not allow. I did not hide that. It is recorded as an accepted, time-boxed risk that expires on the thirty-first of December, with a check script that runs in the CI workflow, which has passed on GitHub. The reasoning is that no image-handling path is reachable: the project never imports Pillow, the interface has no image components, and upload routes are blocked. That is a reasoned exposure assessment, not a fix. This is not production-ready, and it is not certified for anything.

## [C11] Deployment architecture: verified versus proposed (~90 words)
What is verified: the lexical-only container image builds, runs as a non-root user, read-only, with all capabilities dropped, published to loopback only, with a healthy endpoint and security headers. The semantic-mode container has also been run once locally. Still outstanding: an image vulnerability scan; and the GitHub workflow only covers the lexical image. What is only proposed: an AWS design with a single private instance reached through Session Manager, no public ingress. Nothing is deployed on AWS. I checked identity and costs read-only, and I could not verify the credit balance.

## [C12] Closing (~60 words)
This project is a small, honest example of evidence-grounded AI for insurance: grounded retrieval, deterministic rules, validated citations, human review, and an audit trail. Its strongest feature is that it documents what it cannot do. The code, tests, evaluation reports and governance documents are in the repository. The tests run with a single command, and the commands that regenerate the evaluation reports are documented in the readme; the semantic results also need the pinned model to be downloaded first. Thank you for watching.

---
## Portfolio cut (60-90 s, ~180-200 words) - lines reused from the above
C01 first two sentences; C06 first three sentences; C07 "Before any answer is shown..." through "fabricated or altered citation is caught"; C08 "an override requires a written reason" and "never overwritten"; C09 "I wrote these cases myself, so this is not a blind evaluation"; C10 "No authentication... local-only" and the Pillow sentence; C12 last two sentences.
