# Video production status (2026-10-27)

* Written: voiceover script, technical script, shot list, chapters, asset manifest, draft subtitles. **Drafts, awaiting user script review.**
* Narration: **not generated**. ElevenLabs credit balance **not verified** (no read-only balance tool found in the MCP). No credits spent.
* Recordings: none. Rendered video: none. Final SRT: not possible until audio durations are known; `SUBTITLES.srt` is an estimate.
* Script revised after claim check (`VOICEOVER_CLAIM_CHECK.md`). MEASURED from the revised script text: 1,144 spoken words, 7,173 characters (chapters C01-C12: 462, 556, 430, 542, 595, 549, 497, 472, 1068, 926, 537, 539). ESTIMATED duration about 7.9 min at 145 wpm (an estimate; no pauses). Credit cost per character is UNVERIFIED (no supported source in this session); confirm in the ElevenLabs dashboard.
* Do not mark complete until audio and video files exist and have been checked.
* The video must label as outstanding: image vulnerability scan (and that CI covers only the lexical image). Verified: lexical and semantic images run locally, GitHub Actions green on main (`docs/RELEASE_GATES.md`). AWS is PROPOSED only; credit balance unverified.

## ElevenLabs check (2026-10-27, read-only)
* MCP reachable: creative_list_voices returned 25 English educational voices (no generation, no credits spent).
* Credit balance: **not available** through any read-only tool found; must be confirmed by the user in the ElevenLabs dashboard before generation.
* Proposed voice (not yet chosen by user): "Martin - Calm, Clear Narrator" (id akQnlreIUIoJxrTrosJj, professional library voice, calm/steady/informative); alternative "Norman" (software-architect tone). Model and settings to be recorded at generation time.
* Generation plan: one call per chapter (C01-C12), after script approval and balance check; record file names and durations here.


* Voice chosen by user 2026-10-27: Martin - Calm, Clear Narrator (akQnlreIUIoJxrTrosJj). Generation still NOT started; awaiting script approval and balance confirmation.

## Update after evaluation re-run (2026-10-27)
* Re-run completed offline (pytest 588 passed, ruff, mypy, pip check, allowlist gate, eval_variants, calibrate, eval_workflow incl. semantic with the locally present pinned model). Metrics reproduced; see `VOICEOVER_CLAIM_CHECK.md` section 2. Pre-fix German-cue rates (0.836/0.855) are copied from the committed report, not re-run.
* HO25 flagged for a separate, reviewable label decision; label NOT changed (claim check section 4).
* Prepared (not executed): `ELEVENLABS_GENERATION_PLAN.md` (voice Martin, per-chapter characters, one-take C01 test plan). Balance and rate still unverified; no audio generated; no credits spent.
* Prepared: `PORTFOLIO_CUT_OUTLINE.md` (60-90 s). `SUBTITLES.srt` is an INCOMPLETE placeholder covering only a few opening lines of an older script; it is not a synchronized subtitle file.
* Footage still missing: all screen recordings, rendered mermaid diagram, fresh command outputs (S05-S09, S11-S12, S15-S19), Docker evidence capture, final audio. Ready: three Milestone-4 screenshots only.
* AWS: on hold; nothing provisioned; credit balance unverified.
