# Process overview

How the Governed Claims Coverage Engine works from policy documents to an audited, human-reviewed answer. All data is synthetic. The assessor is a deterministic rule engine, not an LLM.

## 1. End to end

```mermaid
flowchart TB
    subgraph PREP["Step 1 - Prepare the corpus (offline)"]
        direction LR
        P1["Synthetic policy PDFs<br/>8 documents, EN / FR / DE"] --> P2["Safe ingestion<br/>type, size, pages,<br/>encryption checks"]
        P2 --> P3["SHA-256 hash<br/>and version"]
        P3 --> P4["Clause-aware chunks<br/>page and clause id kept"]
        P4 --> P5["Search index<br/>BM25 + optional embeddings"]
    end

    subgraph ASK["Step 2 - Answer a question (per request)"]
        direction LR
        Q1["Reviewer question<br/>and chosen policies"] --> W["LangGraph workflow<br/>see section 2"]
        W --> R{"Outcome"}
        R -->|"clause backs the answer"| O1["Supported<br/>preliminary assessment<br/>cited clause, page, hash"]
        R -->|"not enough evidence"| O2["Insufficient evidence<br/>system abstains"]
        R -->|"exception, conflict, unclear"| O4["Human review required"]
        R -->|"unsafe or invalid input"| O3["Request rejected<br/>goes straight to the audit record"]
    end

    subgraph REVIEW["Step 3 - Human review and audit"]
        direction LR
        H["Reviewer approves or overrides<br/>override needs a written reason<br/>original assessment never overwritten"] --> A["Audit record<br/>ids, hashes, flags, workflow path,<br/>review history; question kept only as a hash"]
    end

    subgraph ASSURE["Assurance"]
        direction LR
        E1["Evaluation sets<br/>64 calibration, 55 held-out,<br/>19 adversarial"] ~~~ E2["Automated tests and CI<br/>590 tests"] ~~~ E3["Governance documents<br/>threat model, risk, security review"]
    end

    subgraph RUN["Where it runs"]
        direction LR
        D1["Local Docker<br/>non-root, read-only,<br/>loopback only"] ~~~ D2["Hugging Face Space<br/>public synthetic demo"] ~~~ D3["AWS design<br/>PROPOSED, NOT DEPLOYED"]
    end

    PREP --> ASK --> REVIEW
    REVIEW ~~~ ASSURE
    ASSURE ~~~ RUN
```

## 2. The per-request workflow (LangGraph)

Solid arrows always happen; labelled arrows are the conditional routes in `src/claims_engine/workflow.py`. Every path ends at the audit record.

```mermaid
flowchart TD
    S(["start"]) --> VI["validate_input"]
    VI -->|"invalid"| RJ["reject"]
    VI -->|"valid"| SQ["screen_query"]
    SQ -->|"flagged"| AB["abstain"]
    SQ -->|"clean"| RT["retrieve"]
    RT --> ES["enforce_scope<br/>default-deny"]
    ES -->|"nothing in scope"| AB
    ES -->|"in scope"| SE["screen_evidence"]
    SE --> SC["score_evidence"]
    SC -->|"too weak"| AB
    SC -->|"enough evidence"| AS["assess<br/>deterministic rules"]
    AS --> VC["validate_citations"]
    VC -->|"citation error, retry"| AS
    VC -->|"citation error, give up"| AB
    VC -->|"all citations valid"| HG["human_review_gate"]
    AB --> HG
    HG --> AU["audit"]
    RJ --> AU
    AU --> E(["end"])
```

## 3. What a citation must match

Before any answer is shown, each citation is validated against the passage retrieved for that request: chunk id, document id, SHA-256, version, page, clause, verbatim quote and scope. A valid citation proves the quote is real, not that the clause supports the verdict.

## 4. Scope and limits

Synthetic data only. The demo has no authentication, so it must not be used with real data. The AWS design is a proposal; nothing is deployed on AWS. See `governance/` and `SECURITY_LIMITATIONS.md` for the full list of limits.
