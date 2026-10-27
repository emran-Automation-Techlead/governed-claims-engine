# Portfolio cut outline (60-90 s) - DRAFT, timings are estimates

Goal: show the engineering judgement in one minute: grounded, abstains, reviewable, honest about limits. Uses real app screens and repo files only.
Narration budget about 150-190 words (about 60-75 s at 145 wpm) taken from the full script lines noted. No audio exists.

| Time (est.) | Shot | Source | Narration (from full script) |
|---|---|---|---|
| 0:00-0:08 | Title card, then README top | `README.md` | C01: "a prototype that helps a human reviewer check what an insurance policy says... decision-support tool, not a decision-maker... synthetic policies." |
| 0:08-0:25 | Supported assessment with citation | `docs/screenshot_1_supported_assessment.jpg` or live demo | C06: supported / insufficient / rejected / human review; abstaining is a safeguard, not proof of safety. C07: every citation validated against the retrieved passage. |
| 0:25-0:38 | Off-topic question abstains | live demo (lexical-only) | C05: "Anything that fails a check is rejected or abstains. It does not guess." |
| 0:38-0:50 | Override with reason; original preserved; audit viewer | `docs/screenshot_2_review_override.jpg`, `docs/screenshot_3_audit_viewer.jpg` | C08: override needs a reason; the original assessment is never overwritten. |
| 0:50-1:05 | Evaluation figures with caveat banner | `eval/m3/M3_FINDINGS.md` section 4 | C09: held-out figures, "self-authored, not a blind evaluation". |
| 1:05-1:20 | Limits | `governance/GRADIO_SECURITY_REVIEW.md`, `PILLOW_ADVISORY_REVIEW.md` | C10: no authentication, local-only; Pillow advisories are an accepted, time-boxed risk. |
| 1:20-1:30 | Closing | repo tree | C12: "documents what it cannot do". |

On-screen labels: SYNTHETIC DATA; DETERMINISTIC RULES (NOT AN LLM); IMPLEMENTED+TESTED; AWS = PROPOSED, NOT DEPLOYED (only if mentioned).
Not in the cut: AWS, Docker details (full cut only).
