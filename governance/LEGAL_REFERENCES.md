# Legal references and verification record

**Not legal advice. No compliance, certification or legal-approval claim is made for this prototype, and no definitive legal classification is made.**
Prepared 2026-10-27 (updated the same day after a second verification pass) for an engineering portfolio project
(synthetic data only, offline demo). Anything below that matters for a real deployment must be re-checked against the Official Journal by a lawyer.

## 1. How each statement was verified

| Level | Meaning |
|---|---|
| **V1** | Read this session on an official source: the Commission's *AI Act Service Desk* (consolidated text), EIOPA pages, or the **Official Journal text served by the EU Publications Office** (Cellar). |
| **V2** | Corroborated only by search results/snippets from official domains; the primary page was not read. |
| **V3** | Not verified this session. Must be verified before anyone relies on it. |

**Access history (honest account).**
1. EUR-Lex returned *empty page bodies* to the automated fetch tool for the GDPR, DORA and AI Act. One attempt to get around that by presenting a different browser identity was
   blocked by the environment's safety classifier as bot-check circumvention and **was not retried**; EUR-Lex was not used further.
2. A legitimate alternative was then found: the Publications Office's own resolver (`publications.europa.eu/resource/celex/<CELEX>`) redirects to its Cellar store, which serves the
   Official Journal text. GDPR (Cellar id `3e485e15-11bd-11e6-ba9a-01aa75ed71a1`) and DORA (`0caf473a-85bd-11ed-9887-01aa75ed71a1`) were read in ~100,000-character windows (the
   documents are 800k / 745k characters). Regulation (EU) 2026/1744 (`b459c07f-86fb-11f1-bf5e-01aa75ed71a1`) was read only for its first 100,000 characters (title, recitals).
   The **original** AI Act text (Reg. 2024/1689) was not read; its provisions were read on the Commission's Service Desk, which presents the consolidated text "as at 27 July 2026"
   and states that its summaries are not legally binding.
3. Reading was done through a summarising fetch tool (it paraphrases a window of text on request). Article numbers and structure are therefore well supported, but **exact wording
   should be confirmed in the Official Journal PDF** before quoting.

Primary identifiers (open in an ordinary browser):
AI Act <https://eur-lex.europa.eu/eli/reg/2024/1689/oj> (amended by <https://eur-lex.europa.eu/eli/reg/2026/1744/oj/eng>) -
GDPR <https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng> - DORA <https://eur-lex.europa.eu/eli/reg/2022/2554/oj/eng>.

## 2. EU AI Act - Regulation (EU) 2024/1689, as amended

| Topic | What the source says | Level | Source (accessed 2026-10-27) |
|---|---|---|---|
| Amending act | **Regulation (EU) 2026/1744** of the European Parliament and of the Council **of 8 July 2026** amending Regulations (EU) 2024/1689, (EU) 2018/1139 and (EU) 2023/1230 ("Digital Omnibus on AI"). The OJ header read shows series L, number 2026/1744, dated 24 July 2026 (the page's date, not independently confirmed as the publication date); recital 46: enters into force on the **third day after publication**; recital 40: high-risk (Chapter III Sections 1-3) application moves to **2 December 2027 for Annex III** systems and **2 August 2028 for Annex I** systems. The operative articles were not reached (text window ended). | V1 (title, recitals) | <http://publications.europa.eu/resource/cellar/b459c07f-86fb-11f1-bf5e-01aa75ed71a1.0006.03/DOC_1> |
| Consolidated status | The Service Desk presents the text "as at 27 July 2026", with passages marked **AMENDED/NEW** by the Omnibus. | V1 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-113> |
| Application dates (Art 113, as amended) | Ch. I-II from 2 Feb 2025 (except Art 5(1) first subpara points (ba),(bb) and Art 5(1a),(1b): 2 Dec 2026); Ch. III Section 4, Ch. V, VII, XII and Art 78 from 2 Aug 2025; **Ch. III Sections 1-3 for Art 6(2)/Annex III systems from 2 Dec 2027**, for Art 6(1)/Annex I from 2 Aug 2028; Arts 102-110 from 27 Jul 2026; general application date 2 Aug 2026. *Earlier, un-amended dates (e.g. 2 Aug 2026 for Annex III) are obsolete.* | V1 | same page |
| "AI system" (Art 3(1)) | Computer-based system operating with varying autonomy that, for explicit or implicit objectives, **infers** from inputs how to generate outputs (predictions, content, recommendations, decisions) that can influence environments. Also (3) provider, (4) deployer, (11) putting into service, (12) intended purpose. | V1 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-3> |
| Rule-based software | Commission guidelines on the AI-system definition (29 Jul 2025, C(2025) 5053; non-binding): recital 12 distinguishes AI systems from simpler traditional software; systems based solely on rules defined by natural persons are not covered; assessment is case by case. | V2 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/resource/guidelines-ai-definition> |
| Annex III route (Art 6(2)) and derogation (6(3)-(4)) | Annex III systems are high-risk unless the 6(3) derogation applies (narrow procedural task / improving a completed human activity / detecting deviations without replacing human assessment / preparatory task); **any Annex III system that profiles natural persons is always high-risk**; a provider relying on the derogation must document the assessment beforehand and register under Art 49(2). | V1 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6> |
| Annex III point 5 | (a) public assistance, (b) creditworthiness (fraud detection excluded), **(c) risk assessment and pricing in relation to natural persons in the case of life and health insurance**, (d) emergency calls/triage. Other insurance lines are not named. | V1 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3> |
| Claims systems vs 5(c) | Commission guidance (non-binding, undated page): claims-management systems that check claim validity under policy terms or determine payout are *distinct from* risk assessment and pricing and are not 5(c), even though outcomes affect the benefit. | V1 (guidance) | <https://ai-act-service-desk.ec.europa.eu/en/essential-services> |
| Pending proposal | EIOPA asked for human-supervised GLMs/GAMs to be excluded from 5(c); the Commission had not acted. Not law. | V2 | EIOPA letter (search listing) |
| Record-keeping (Art 12) | High-risk systems must technically support automatic event logging over their lifetime, with traceability appropriate to the intended purpose, to identify risk situations/substantial modifications, support post-market monitoring (Art 72) and deployer monitoring (Art 26(5)). | V1 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-12> |
| Human oversight (Art 14) | Effective oversight by natural persons by design; overseers must understand capabilities/limits, stay aware of **automation bias**, interpret output, be able to disregard/override/reverse it, and intervene/stop. Unchanged by the Omnibus. | V1 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-14> |
| Deployer duties (Art 26) | Use per instructions; assign oversight to competent, trained, authorised people; relevant input data; monitor and report; **keep automatically generated logs at least six months** (unless other law requires otherwise); inform affected natural persons for Annex III systems that make or assist decisions about them; cooperate with authorities. | V1 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-26> |
| Fundamental-rights impact assessment (Art 27) | Required before first use for deployers that are public bodies or private entities providing public services **and for deployers of high-risk systems under Annex III points 5(b) and 5(c)**; content: processes, duration/frequency, affected groups, specific risks, human oversight, measures if risks materialise; notification of the market-surveillance authority (para 3) and the link to a GDPR DPIA (para 4) are marked AMENDED. | V1 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-27> |
| Transparency (Art 50) | Providers must ensure people know they interact with an AI system (unless obvious) and mark synthetic content; deployers have duties for emotion recognition/biometric categorisation and deepfakes/public-interest text; only para 7 amended. Application date not stated on the page. | V1 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50> |
| AI literacy (Art 4) | Providers **and deployers** "shall take measures" to support AI literacy of staff and others operating AI on their behalf (all paragraphs AMENDED). | V1 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-4> |
| Penalties (Art 99) | Prohibited practices up to EUR 35m / 7 %; other operator obligations (incl. deployers and Art 50) up to EUR 15m / 3 %; incorrect information to authorities up to EUR 7.5m / 1 % (whichever is higher; for SMEs whichever is lower; para 6a **NEW** extends the "lower" rule to small mid-caps). | V1 | <https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-99> |
| Not read | Art 5 text; Arts 9-11, 13, 15 (risk management, data governance, technical documentation, instructions, accuracy/robustness/cybersecurity); Arts 72-73; GPAI chapter; the original OJ text. | V3 | - |

## 3. GDPR - Regulation (EU) 2016/679

All rows read in the Official Journal text (Cellar), **V1**, unless stated. Source: <http://publications.europa.eu/resource/cellar/3e485e15-11bd-11e6-ba9a-01aa75ed71a1.0006.03/DOC_1>.

| Topic | Statement |
|---|---|
| Art 4(1) | Personal data: any information relating to an identified or identifiable natural person. |
| Art 5(1)(a)-(f) | Lawfulness/fairness/transparency; purpose limitation; data minimisation; accuracy; storage limitation; integrity and confidentiality. |
| Art 6(1) | Lawful bases: consent, contract, legal obligation, vital interests, public interest/official authority, legitimate interests. |
| Art 9(1)-(2) | Special categories incl. **data concerning health** are prohibited unless an Art 9(2) exception applies. |
| Art 12-15 | Transparent information; Art 13(2)(f), 14(2)(g), 15(1)(h): existence of automated decision-making incl. profiling and, at least then, **meaningful information about the logic involved**, significance and envisaged consequences. |
| **Art 22(1)-(4)** | Right not to be subject to a decision **based solely on automated processing**, including profiling, which produces legal effects or similarly significantly affects the person. Not applicable if necessary for a contract, authorised by Union/Member State law with suitable safeguards, or based on explicit consent (22(2)); for contract/consent cases the controller must provide at least the right to **human intervention, to express a view and to contest** (22(3)); special-category data only under Art 9(2)(a)/(g) with safeguards (22(4)). |
| Art 25(1)-(2) | Data protection by design and by default (e.g. pseudonymisation, data minimisation; only necessary data per purpose). |
| Art 28(1), 30, 32 | Processors with sufficient guarantees; records of processing (exemption for < 250 staff unless risky/not occasional/special categories); security appropriate to risk. |
| Art 33(1) | Notify the supervisory authority of a breach without undue delay and, where feasible, within **72 hours**. |
| Art 35(1), (3) | DPIA where processing is likely to result in high risk; (3)(a) systematic extensive evaluation/profiling with automated decisions that significantly affect people; (3)(b) large-scale special categories. |
| Art 44 | General principle for transfers to third countries (Arts 45-46 text not read). |
| Art 83(4), (5) | Fines up to EUR 10m / 2 % and EUR 20m / 4 % of worldwide annual turnover (higher figure) for the respective tiers. |
| Art 99 | Enters into force on the twentieth day after publication; **applies from 25 May 2018**. |
| Guidance on "solely automated" / meaningful human involvement | The EDPB page lists the Article 29 WP guidelines on automated decision-making and profiling (endorsed 25 May 2018; WP251rev.01) and only links to a PDF. **The guideline text was not read**, so what counts as meaningful human involvement is not verified here (**V3**). Related CJEU judgments C-634/21 and C-203/22 were seen only as search snippets (V2). |
| Luxembourg | The national supervisory authority (CNPD) and the insurance supervisor (CAA) were **not researched**. |

## 4. DORA - Regulation (EU) 2022/2554

All rows read in the Official Journal text (Cellar), **V1**, unless stated. Source: <http://publications.europa.eu/resource/cellar/0caf473a-85bd-11ed-9887-01aa75ed71a1.0006.03/DOC_1>
(OJ L 333, 27.12.2022).

| Topic | Statement |
|---|---|
| Art 1 | Uniform requirements for ICT risk management, incident reporting, resilience testing, information sharing, third-party risk and contractual arrangements, oversight of critical ICT third-party providers. |
| **Art 2(1)** | Applies to points (a)-(u), including **(n) insurance and reinsurance undertakings**, **(o) insurance, reinsurance and ancillary insurance intermediaries**, and (u) ICT third-party service providers. Art 2(2): "financial entities" = points (a)-(t). |
| **Art 2(3)** | Does **not** apply to, among others, **(b) insurance and reinsurance undertakings referred to in Article 4 of Directive 2009/138/EC (Solvency II)** and **(e) insurance/reinsurance/ancillary intermediaries that are micro, small or medium-sized enterprises**. Whether a specific insurer falls under the Art 4 carve-out depends on Solvency II thresholds, which were **not researched** (V3). EIOPA's 2024 Opinion on DORA scope vs the Solvency II review is V2 (search listing). |
| Art 3 | "ICT asset": software or hardware asset in the network and information systems used by the financial entity; "ICT third-party service provider": undertaking providing ICT services. |
| Arts 5-6, 8-12 | Management-body responsibility; ICT risk management framework; identification (functions, assets, dependencies); protection and prevention (monitoring, access restriction, strong authentication, encryption, change management, patching); detection; response and recovery (continuity policy, plans tested at least yearly); backup and restoration. |
| Arts 17-19 | ICT-related incident management process; classification by impact criteria; reporting of major incidents (initial, intermediate, final) to the competent authority. |
| Arts 24-25 | Risk-based digital operational resilience testing programme (independent parties, at least yearly for systems supporting critical/important functions); methods incl. vulnerability assessments, scenario tests, penetration testing. |
| Arts 29-30 | Preliminary assessment of ICT concentration risk; key contractual provisions with ICT third-party providers (service description, data location, security, access/return of data, incident assistance, cooperation, termination rights, exit strategies for critical/important functions). Art 28 text not paraphrased (V3). |
| Art 64 | Enters into force on the twentieth day after publication; **applies from 17 January 2025**. |
| EIOPA | Confirms application on 17 Jan 2025 and the five pillars; scope is entity-based (Q&A, V2). <https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en> (V1) |

## 5. What this means for this prototype (engineering analysis, not a legal conclusion)

1. **Is it an "AI system" under the AI Act?** The deterministic assessor consists of rules written by a person; under the Commission's guidance such software is *likely* outside the
   definition (V2). The optional multilingual embedding model is a trained neural network that infers representations from inputs, so a system *including* it **may** be an AI system.
   **Unresolved; no conclusion is drawn.**
2. **If it were an AI system, would it be high-risk?** Annex III 5(c) covers life/health *risk assessment and pricing*; Commission guidance says claims-validity/payout systems are generally
   not 5(c) (V1). The prototype performs preliminary clause matching on synthetic data and is not placed on the market. Classification turns on **intended purpose**: using it for underwriting,
   pricing or profiling of individuals would change the analysis (Art 6(3) profiling rule). **No Annex III classification is asserted.** If a deployer did use a 5(c) system, Arts 26-27 (logs >= 6 months,
   fundamental-rights impact assessment) would be among the deployer's duties.
3. **Timing.** Annex III high-risk obligations now start 2 Dec 2027 (V1); Art 4 AI literacy and (if applicable) Art 50 are earlier.
4. **GDPR.** The demo uses synthetic data only, so GDPR is not engaged by the demo itself. Real claims data (names, **health data - Art 9**) would trigger the controls in `DATA_PROTECTION.md`.
   The design (mandatory human review; no solely-automated decision) is aimed at Art 22; whether that review is *meaningful* in the guidance's sense is **not verified** and depends on process,
   training and automation-bias controls (Art 14(4)(b) of the AI Act names the same risk).
5. **DORA.** Obligations bind the **financial entity** (and ICT third-party providers by contract), not a code repository. Insurers are within Art 2(1)(n) unless Art 2(3)(b) applies (undetermined here).
   If an in-scope insurer adopted this software it would become an ICT asset (Art 3) within its ICT risk framework, and a vendor would be an ICT third-party service provider subject to Art 30 contracts.
   `OPERATIONAL_RESILIENCE.md` lists helpful engineering practices without claiming compliance.

## 6. Legal obligations vs engineering practices

| Area | Legal obligation (who, when) | Engineering practice in this repo | Implemented and tested? |
|---|---|---|---|
| Human oversight | AI Act Art 14 for *high-risk* systems (Annex III from 2 Dec 2027) - provider design duty | Mandatory-review routing, override with required reason, automation-bias wording, "not a claim decision" labels | Yes (workflow + demo tests). Not evidence of Art 14 compliance |
| Transparency | AI Act Art 50 where applicable | Banner stating synthetic/deterministic/non-binding; audit shows model/prompt/policy versions | Yes (UI tests); applicability not established |
| Logging / traceability | AI Act Art 12 and Art 26(6) (logs >= 6 months) for high-risk systems; DORA ICT logging for in-scope entities | Structured audit records; optional hash-chained log | Yes for the records and chain; **retention, access control and external anchoring not implemented** |
| Data protection | GDPR for personal data (Arts 5, 22, 25, 30, 32, 33, 35) | Synthetic only; question text never stored; pseudonymous reviewer ids | Yes for those controls; no data-subject-rights tooling, no DPIA |
| Security / resilience | GDPR Art 32; DORA Arts 5-12, 17-19, 24-25, 29-30 for financial entities | Pinned/hashed dependencies, CI audit with time-boxed allowlist, hardened container configuration, scope enforcement, blocked upload routes | Partly; **container image never built or run** |
| Fundamental-rights impact assessment | AI Act Art 27 for deployers of 5(b)/5(c) high-risk systems | None | No |
| AI literacy | AI Act Art 4 (providers and deployers) | None for people (documentation only) | No |
</content>
