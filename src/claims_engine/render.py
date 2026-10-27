"""HTML rendering for the demo. EVERYTHING that comes from a document, a question or a reviewer is
passed through html.escape: policy text is untrusted and must never be rendered as markup."""
from __future__ import annotations

from collections.abc import Sequence
from html import escape as esc

from .demo_service import LIMITATIONS, DemoService, DocOption, ReviewEntry, Run
from .schemas import AssessmentStatus, EvidenceRef, ResultKind

STATUS_LABEL = {
    AssessmentStatus.POTENTIALLY_COVERED.value: "Potentially covered",
    AssessmentStatus.POTENTIALLY_EXCLUDED.value: "Potentially excluded",
    AssessmentStatus.INSUFFICIENT_EVIDENCE.value: "Insufficient evidence",
    AssessmentStatus.HUMAN_REVIEW_REQUIRED.value: "Human review required",
}
FLAG_HELP = {
    "query:": "instruction-like or obfuscated content in the question",
    "evidence:": "instruction-like content inside a retrieved policy passage",
    "scope_violation": "retrieval returned a passage outside the selected documents",
    "citation_validation_failed": "the proposed citations did not match the retrieved evidence",
}


def limitations_html(compact: bool = False) -> str:
    items = "".join(f"<li>{esc(x)}</li>" for x in LIMITATIONS)
    head = "<b>Read first - this is a synthetic, non-production demonstration.</b>"
    return (f'<div class="ce-banner">{head}<ul>{items}</ul></div>' if not compact else
            f'<div class="ce-banner ce-compact">{head} Synthetic data, deterministic cautious assessor, '
            "self-authored evaluation, no authentication, not production-ready or legally certified. "
            "See the <i>About &amp; limitations</i> tab.</div>")


def scope_md(selected: Sequence[DocOption]) -> str:
    if not selected:
        return ("**Scope: none selected.** Choose at least one document - the system never searches "
                "documents you did not select.")
    lines = [f"**Scope: {len(selected)} document(s). Only these will be searched or cited:**"]
    lines += [f"- `{d.filename}` - {d.title} [{d.language}], version {d.version}, "
              f"sha256 `{d.sha256[:12]}...`" + (" - **adversarial test document**" if d.adversarial else "")
              for d in selected]
    return "\n".join(lines)


def _flag_explanations(flags: Sequence[str]) -> str:
    if not flags:
        return ""
    rows = []
    for f in flags:
        why = next((v for k, v in FLAG_HELP.items() if f.startswith(k)), "guardrail triggered")
        rows.append(f"<li><code>{esc(f)}</code> - {esc(why)}</li>")
    return f'<div class="ce-flags"><b>Guardrail flags</b><ul>{"".join(rows)}</ul></div>'


def status_html(run: Run, mode: str) -> str:
    r = run.result
    chips = (f'<span class="ce-chip">review priority: <b>{esc(r.review_priority.upper())}</b></span>'
             f'<span class="ce-chip">retrieval: {esc(mode)}</span>'
             f'<span class="ce-chip">trace {esc(r.trace_id[:8])}</span>')
    if r.kind == ResultKind.REJECTED:
        return (f'<div class="ce-status ce-bad"><div class="ce-title">REQUEST REJECTED - nothing was assessed</div>'
                f'<div>{esc(r.reject_reason or "")}</div><div class="ce-chips">{chips}</div></div>')
    a = r.assessment
    if a is None:  # invariant of WorkflowResult; explicit so it survives python -O
        raise RuntimeError("non-rejected result without an assessment")
    label = STATUS_LABEL[a.status.value]
    if r.kind == ResultKind.ASSESSED:
        cls, title = "ce-ok", "SUPPORTED PRELIMINARY ASSESSMENT"
        sub = (f"<div class='ce-big'>{esc(label)}</div>"
               "<div>Based on the cited clause(s) below. Still pending human review - this is not a claim decision.</div>")
    elif a.status == AssessmentStatus.INSUFFICIENT_EVIDENCE:
        cls, title = "ce-neutral", "INSUFFICIENT EVIDENCE - NO ASSESSMENT PRODUCED"
        sub = "<div>The selected documents do not contain a sufficiently related clause. Nothing is concluded.</div>"
    else:
        cls, title = "ce-warn", "HUMAN REVIEW REQUIRED - NO AUTOMATED ASSESSMENT"
        sub = "<div>The system declined to decide. A person must look at this case.</div>"
    return (f'<div class="ce-status {cls}"><div class="ce-title">{title}</div>{sub}'
            f'<div class="ce-chips">{chips}</div></div>')


def reasons_html(run: Run) -> str:
    a = run.result.assessment
    if a is None:
        return ""
    parts = []
    if a.escalation_reason:
        parts.append(f"<p><b>Reason for escalation:</b> {esc(a.escalation_reason)}</p>")
    if a.uncertainty:
        parts.append(f"<p><b>Uncertainty:</b> {esc(a.uncertainty)}</p>")
    if a.missing_information:
        items = "".join(f"<li>{esc(m)}</li>" for m in a.missing_information)
        parts.append(f"<p><b>Missing information / things to verify:</b></p><ul>{items}</ul>")
    parts.append(f"<p><b>Summary:</b> {esc(a.summary)}</p>")
    parts.append(f'<p class="ce-fine">{esc(a.disclaimer)} Produced by <code>{esc(a.model_version)}</code> '
                 f"(deterministic rules, no language model). Abstention policy "
                 f"<code>{esc(str(run.result.audit.retrieval.params.get('abstain_policy', '?')) if run.result.audit.retrieval else '?')}</code>.</p>")
    parts.append(_flag_explanations(run.result.audit.guardrail_flags))
    if run.result.quarantined_chunk_ids:
        parts.append(f'<p class="ce-warnline">{len(run.result.quarantined_chunk_ids)} retrieved passage(s) '
                     "were quarantined by the injection tripwire and are NOT shown or used.</p>")
    if run.result.notices:
        parts.append("".join(f'<p class="ce-fine">{esc(n)}</p>' for n in run.result.notices))
    return f'<div class="ce-reasons">{"".join(parts)}</div>'


def _card(e: EvidenceRef, doc: DocOption | None, cls: str, tag: str) -> str:
    where = f"{esc(doc.filename)} - v{esc(doc.version)}" if doc else esc(e.doc_id)
    clause = esc(e.clause_id) if e.clause_id else "(no clause id)"
    return (f'<div class="ce-card {cls}"><div class="ce-card-h">Clause {clause} - page {e.page_number} '
            f'<span class="ce-tag">{esc(tag)}</span></div>'
            f'<div class="ce-card-m">{where} - sha256 {esc(e.doc_sha256[:12])}... - chunk {esc(e.chunk_id)}</div>'
            f"<blockquote>{esc(e.quote)}</blockquote></div>")


def evidence_html(run: Run) -> str:
    a = run.result.assessment
    docs = {d.doc_id: d for d in run.scope}
    cited_ids: set[str] = set()
    blocks: list[str] = []
    if a is not None and a.supporting_clauses:
        blocks.append("<h4>Supporting clauses (cited)</h4>")
        for e in a.supporting_clauses:
            cited_ids.add(e.chunk_id)
            blocks.append(_card(e, docs.get(e.doc_id), "ce-cite-sup", "supports cover"))
    if a is not None and a.exclusions_and_limitations:
        blocks.append("<h4>Exclusions / limitations (cited)</h4>")
        for e in a.exclusions_and_limitations:
            cited_ids.add(e.chunk_id)
            blocks.append(_card(e, docs.get(e.doc_id), "ce-cite-exc", "exclusion / limit"))
    others = [e for e in run.result.retrieved if e.chunk_id not in cited_ids]
    if others:
        blocks.append("<details><summary>Other passages considered but not cited "
                      f"({len(others)})</summary>")
        blocks += [_card(e, docs.get(e.doc_id), "ce-cite-other", "not cited") for e in others]
        blocks.append("</details>")
    if not blocks:
        blocks.append('<p class="ce-fine">No evidence is shown because none was cited.</p>')
    return f'<div class="ce-evidence">{"".join(blocks)}</div>'


def proposed_html(run: Run | None) -> str:
    if run is None:
        return '<p class="ce-fine">No assessment selected yet - run one on the first tab.</p>'
    a = run.result.assessment
    if a is None:
        return ('<div class="ce-status ce-bad"><div class="ce-title">Nothing to review</div>'
                "<div>The request was rejected, so there is no proposed assessment.</div></div>")
    cited = len(a.supporting_clauses) + len(a.exclusions_and_limitations)
    return (f'<div class="ce-card ce-cite-other"><div class="ce-card-h">Proposed assessment (original, kept unchanged)</div>'
            f"<p><b>{esc(STATUS_LABEL[a.status.value])}</b> - {esc(a.summary)}</p>"
            f'<div class="ce-card-m">trace {esc(run.result.trace_id)} - {cited} cited clause(s) - '
            f"review priority {esc(run.result.review_priority)}</div></div>")


def reviews_html(run: Run | None) -> str:
    if run is None or not run.reviews:
        return '<p class="ce-fine">No review recorded for this assessment yet.</p>'
    rows = []
    for e in reversed(run.reviews):
        eff = STATUS_LABEL.get(e.effective_status or "", "-")
        over = f" -> overridden to <b>{esc(STATUS_LABEL[e.override_status])}</b>" if e.override_status else ""
        rows.append(
            f'<div class="ce-card ce-cite-sup"><div class="ce-card-h">RECORDED DEMONSTRATION REVIEW - '
            f"{esc(e.action.upper())}{over}</div>"
            f"<div>Proposed: <b>{esc(STATUS_LABEL[e.proposed_status])}</b> | effective after review: "
            f"<b>{esc(eff)}</b></div>"
            f'<div class="ce-card-m">by {esc(e.reviewer_id)} (unauthenticated) at '
            f"{e.timestamp:%Y-%m-%d %H:%M:%S} UTC</div>"
            + (f"<blockquote>{esc(e.reason)}</blockquote>" if e.reason else "")
            + '<div class="ce-fine">Demonstration record only. This is NOT a legally binding insurance '
              "decision and has no effect outside this session.</div></div>")
    return "".join(rows)


def audit_summary_html(data: dict | None) -> str:
    if data is None:
        return '<p class="ce-fine">Select a trace to view its audit record.</p>'
    docs = "".join(f"<li><code>{esc(str(d['filename']))}</code> v{esc(str(d['version']))} - "
                   f"sha256 <code>{esc(d['sha256'])}</code></li>" for d in data["documents"]) or "<li>(none)</li>"
    chunks = "".join(f"<li><code>{esc(c)}</code></li>" for c in data["retrieved_chunk_ids"]) or "<li>(none)</li>"
    flags = ", ".join(esc(f) for f in data["guardrail_flags"]) or "none"
    rev = ""
    for e in data["review_history"]:
        rev += (f"<li>{esc(e['timestamp_utc'])} - {esc(e['reviewer_id'])} - <b>{esc(e['action'])}</b> "
                f"(proposed {esc(e['proposed_status'])} -> effective {esc(str(e['effective_status']))})"
                + (f" - reason: {esc(e['reason'])}" if e["reason"] else "") + "</li>")
    rev = rev or "<li>no review recorded</li>"
    return (f'<div class="ce-audit"><table>'
            f"<tr><th>Trace ID</th><td><code>{esc(data['trace_id'])}</code></td></tr>"
            f"<tr><th>Recorded</th><td>{esc(data['recorded_at_utc'])} UTC</td></tr>"
            f"<tr><th>Outcome</th><td>{esc(str(data['assessment_status']))} ({esc(data['result_kind'])}), "
            f"review priority {esc(data['review_priority'])}</td></tr>"
            f"<tr><th>Escalation reason</th><td>{esc(str(data['escalation_reason']))}</td></tr>"
            f"<tr><th>Documents (hash + version)</th><td><ul>{docs}</ul></td></tr>"
            f"<tr><th>Retrieved evidence ids</th><td><ul>{chunks}</ul></td></tr>"
            f"<tr><th>Guardrail flags</th><td>{flags}</td></tr>"
            f"<tr><th>Workflow path</th><td>{esc(' -> '.join(data['node_path']))}</td></tr>"
            f"<tr><th>Question</th><td>SHA-256 <code>{esc(str(data['question_sha256']))}</code> "
            "(the question text itself is <b>not stored</b>)</td></tr>"
            f"<tr><th>Review history</th><td><ul>{rev}</ul></td></tr></table></div>")


def review_entry_text(e: ReviewEntry) -> str:
    return f"{e.action} by {e.reviewer_id}"


CSS = """
.ce-banner{border:2px solid #b45309;background:rgba(245,158,11,.12);border-radius:8px;padding:10px 14px;margin-bottom:8px}
.ce-banner ul{margin:6px 0 0 18px}.ce-compact{padding:6px 12px;font-size:.92em}
.ce-status{border-radius:10px;padding:14px 16px;border:2px solid;margin-bottom:10px}
.ce-title{font-weight:700;letter-spacing:.03em;margin-bottom:4px}.ce-big{font-size:1.5em;font-weight:700;margin:4px 0}
.ce-ok{border-color:#15803d;background:rgba(34,197,94,.12)}.ce-warn{border-color:#b91c1c;background:rgba(239,68,68,.12)}
.ce-neutral{border-color:#6b7280;background:rgba(107,114,128,.14)}.ce-bad{border-color:#7f1d1d;background:rgba(127,29,29,.16)}
.ce-chips{margin-top:8px}.ce-chip{display:inline-block;border:1px solid #888;border-radius:999px;padding:1px 10px;margin-right:6px;font-size:.82em}
.ce-card{border:1px solid #888;border-left-width:6px;border-radius:6px;padding:8px 12px;margin:8px 0}
.ce-cite-sup{border-left-color:#15803d}.ce-cite-exc{border-left-color:#b45309}.ce-cite-other{border-left-color:#6b7280}
.ce-card-h{font-weight:700}.ce-card-m,.ce-fine{font-size:.82em;opacity:.85}.ce-tag{font-weight:400;font-size:.8em;border:1px solid #888;border-radius:4px;padding:0 6px;margin-left:6px}
.ce-evidence blockquote,.ce-card blockquote{margin:6px 0;padding:6px 10px;border-left:3px solid #888;background:rgba(128,128,128,.10);white-space:pre-wrap}
.ce-warnline{color:#b91c1c;font-weight:600}.ce-audit table{border-collapse:collapse;width:100%}
.ce-audit th{text-align:left;vertical-align:top;width:210px;padding:4px 8px;border-bottom:1px solid #8884}.ce-audit td{padding:4px 8px;border-bottom:1px solid #8884}
"""


def doc_choices(service: DemoService) -> list[tuple[str, str]]:
    return [(d.label, d.doc_id) for d in service.documents()]
