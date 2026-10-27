r"""Offline Gradio demo of the Milestone-3 workflow.

Run (project venv):   .venv\Scripts\python -m claims_engine.app            # http://127.0.0.1:7860
Optional:             --semantic   (needs the fetched local model)   --port N   --audit-log PATH

Binds to 127.0.0.1 only, no share link, Gradio analytics/version-check disabled, system fonts only
(no CDN), no file upload (hostile-PDF ingestion is untested), no network calls. Demo, not production.
"""
from __future__ import annotations

import argparse
import os
import re

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")  # must precede the gradio import
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import gradio as gr

from . import render
from .demo_service import EXAMPLES, DemoService
from .schemas import AssessmentStatus

TITLE = "Governed Claims Coverage Engine - synthetic demo"
STATUS_CHOICES = [(render.STATUS_LABEL[s.value], s.value) for s in AssessmentStatus]
DEFAULT_SCOPE = "synthetic_home_policy.pdf"


def _err(msg: str) -> str:
    from html import escape

    return f'<div class="ce-status ce-bad"><div class="ce-title">Not recorded</div><div>{escape(msg)}</div></div>'


def _ok(msg: str) -> str:
    from html import escape

    return f'<div class="ce-status ce-ok"><div class="ce-title">{escape(msg)}</div></div>'


def make_handlers(service: DemoService) -> dict:
    """Plain functions bound to the UI events. Tested directly AND through a live gradio_client."""
    by_file = {d.filename: d.doc_id for d in service.documents()}

    def dd(trace_id: str | None):
        return gr.update(choices=service.recent(), value=trace_id)

    def on_scope(doc_ids):
        return render.scope_md(service.scope_of(doc_ids or []))

    def on_example(label):
        for lbl, files, question, _ in EXAMPLES:
            if lbl == label:
                ids = [by_file[f] for f in files if f in by_file]
                return question, ids, render.scope_md(service.scope_of(ids))
        return gr.update(), gr.update(), gr.update()

    def on_assess(query, doc_ids, state):
        run = service.assess(query, doc_ids)  # new run, new trace id: nothing is reused
        tid = run.result.trace_id
        return (render.status_html(run, service.mode), render.reasons_html(run), render.evidence_html(run),
                {"trace_id": tid}, render.proposed_html(run), render.reviews_html(run), "", dd(tid))

    def on_review(state, reviewer, action, override_status, reason):
        tid = (state or {}).get("trace_id")
        action_key = {"Approve": "approve", "Override": "override"}.get(action or "", "")
        entry, error = service.review(tid, reviewer, action_key, override_status, reason)
        run = service.get(tid)
        if error:
            return _err(error), render.reviews_html(run), dd(tid)
        return (_ok("Demonstration review recorded (not a binding decision)"),
                render.reviews_html(run), dd(tid))

    def on_audit(trace_id):
        data = service.audit(trace_id)
        return render.audit_summary_html(data), (data or {})

    def on_refresh(state):
        tid = (state or {}).get("trace_id")
        return dd(tid)

    return {"scope": on_scope, "example": on_example, "assess": on_assess, "review": on_review,
            "audit": on_audit, "recent": on_refresh}


def build_app(service: DemoService) -> gr.Blocks:
    h = make_handlers(service)
    options = service.documents()
    default_ids = [d.doc_id for d in options if d.filename == DEFAULT_SCOPE]
    with gr.Blocks(title=TITLE, analytics_enabled=False) as demo:
        gr.Markdown(f"# {TITLE}")
        gr.HTML(render.limitations_html(compact=True))
        state = gr.State({"trace_id": None})
        with gr.Tabs():
            with gr.Tab("1 - Assess"):
                with gr.Row():
                    with gr.Column(scale=2):
                        docs = gr.CheckboxGroup(choices=render.doc_choices(service), value=default_ids,
                                                label="Policy documents in scope (synthetic)")
                        scope = gr.Markdown(render.scope_md(service.scope_of(default_ids)))
                        example = gr.Dropdown(choices=[e[0] for e in EXAMPLES], value=None,
                                              label="Load a synthetic example (optional)")
                        question = gr.Textbox(lines=4, max_length=2000,
                                              label="Question or synthetic scenario (max 2000 characters)",
                                              placeholder="e.g. burst pipes sudden accidental escape water. "
                                                          "Do not enter real personal data.")
                        go = gr.Button("Assess", variant="primary")
                    with gr.Column(scale=3):
                        status = gr.HTML(label="Result")
                        reasons = gr.HTML()
                        evidence = gr.HTML()
            with gr.Tab("2 - Human review (demonstration)"):
                gr.HTML('<div class="ce-banner ce-compact"><b>Demonstration review.</b> What you record here is '
                        "a demo record, <b>not a legally binding insurance decision</b>. The original "
                        "assessment is kept unchanged next to your outcome.</div>")
                proposed = gr.HTML(render.proposed_html(None))
                with gr.Row():
                    reviewer = gr.Textbox(label="Reviewer id (pseudonym; unauthenticated)", value="reviewer-1",
                                          max_length=64)
                    action = gr.Radio(["Approve", "Override"], value="Approve", label="Action")
                    override_status = gr.Dropdown(STATUS_CHOICES, value=None,
                                                  label="Override to status (Override only)")
                reason = gr.Textbox(lines=3, max_length=1000,
                                    label="Explanation (required for Override, min 10 characters; "
                                          "do not enter personal data)")
                submit = gr.Button("Record review", variant="primary")
                review_msg = gr.HTML()
                history = gr.HTML(render.reviews_html(None))
            with gr.Tab("3 - Audit"):
                gr.Markdown("Audit records hold ids, hashes and flags. The question text is **not stored** "
                            "(only its SHA-256).")
                trace = gr.Dropdown(choices=service.recent(), label="Trace", value=None, allow_custom_value=True)
                refresh = gr.Button("Refresh list")
                audit_html = gr.HTML(render.audit_summary_html(None))
                with gr.Accordion("Raw audit record (JSON)", open=False):
                    audit_json = gr.JSON()
            with gr.Tab("About & limitations"):
                gr.HTML(render.limitations_html())
                gr.Markdown(
                    "**How it works.** validate input -> screen the question -> retrieve only inside the selected "
                    "documents -> re-check scope -> screen retrieved text -> evidence-support gate (calibrated "
                    "thresholds) -> deterministic rule-based assessment -> citation validation (bounded retry) -> "
                    "abstain or flag for review -> audit. Every result is a preliminary interpretation.\n\n"
                    "**What 'supported' means.** A cited clause cleared the evidence gate and the rules found it "
                    "grants or excludes cover. It does not mean the claim is valid.\n\n"
                    "**Why it often abstains.** The baseline is deliberately cautious: wording that is not close to "
                    "the clause text is not answered. That is a known limitation, not a bug.\n\n"
                    "See `SECURITY_LIMITATIONS.md` and `eval/m3/M3_FINDINGS.md` in the repository.")

        docs.change(h["scope"], docs, scope, api_name="scope", show_progress="hidden")
        example.change(h["example"], example, [question, docs, scope], api_name="example",
                       show_progress="hidden")
        go.click(h["assess"], [question, docs, state],
                 [status, reasons, evidence, state, proposed, history, review_msg, trace], api_name="assess")
        submit.click(h["review"], [state, reviewer, action, override_status, reason],
                     [review_msg, history, trace], api_name="review")
        trace.change(h["audit"], trace, [audit_html, audit_json], api_name="audit")
        refresh.click(h["recent"], state, trace, api_name="recent")
    return demo


CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; "
       "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; "
       "connect-src 'self'; worker-src 'self' blob:; media-src 'self' data: blob:; "
       "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
_PRECONNECT = re.compile(r"<link\b[^>]*?rel=\"preconnect\"[^>]*?>", re.DOTALL)
_IFRAME_RESIZER = re.compile(r"<script\b[^>]*?iframeResizer[^>]*?>\s*</script>", re.DOTALL)
_OG_IMAGE = re.compile(r"https://raw\.githubusercontent\.com/[^\"']+")


def harden_html(text: str) -> str:
    """Remove the third-party references Gradio's page template ships with (none are needed here)."""
    text = _PRECONNECT.sub("", text)
    text = _IFRAME_RESIZER.sub("", text)
    return _OG_IMAGE.sub("", text)


# Gradio ships routes this UI never uses: an UNAUTHENTICATED file-upload endpoint (stores files in its temp dir), file
# serving, and an icon resizer that calls Pillow. They are blocked here (compensating control for the accepted Pillow
# advisories and against disk filling); see governance/PILLOW_ADVISORY_REVIEW.md. The UI uses none of them.
BLOCKED_PATH_PREFIXES = ('/gradio_api/upload', '/upload', '/gradio_api/file', '/file=', '/file/', '/pwa_icon',
                         '/gradio_api/pwa_icon', '/gradio_api/resource')

LOOPBACK_HOSTS = ('127.0.0.1', 'localhost', '::1')


def check_host(host: str) -> None:
    """Binding anywhere but loopback needs an explicit opt-in: the app has NO authentication."""
    if host not in LOOPBACK_HOSTS and os.environ.get('CLAIMS_ALLOW_NONLOOPBACK') != '1':
        raise SystemExit(
            f'Refusing to bind to {host!r}: this demo has no authentication. Bind to 127.0.0.1, or set '
            'CLAIMS_ALLOW_NONLOOPBACK=1 only when the port is published to loopback / protected by an '
            'authenticating reverse proxy (see governance/GRADIO_SECURITY_REVIEW.md).')


def build_server_app(service: DemoService):
    from fastapi import FastAPI, Request, Response

    api = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @api.get('/healthz')
    def healthz() -> dict:  # liveness only: no data, no state
        return {'status': 'ok'}

    @api.middleware("http")
    async def hardening(request: Request, call_next):
        if request.url.path.lower().startswith(BLOCKED_PATH_PREFIXES):
            seen = 0  # drain a bounded amount of the body so the client reliably sees the 404, not a reset
            async for chunk in request.stream():
                seen += len(chunk)
                if seen > 1_048_576:
                    break
            blocked = Response('{"detail":"disabled in this deployment"}', status_code=404,
                               media_type='application/json')
            blocked.headers.update({'Content-Security-Policy': CSP, 'Cache-Control': 'no-store',
                                    'X-Content-Type-Options': 'nosniff'})
            return blocked
        resp = await call_next(request)
        headers = dict(resp.headers)
        headers.update({"Content-Security-Policy": CSP, "X-Frame-Options": "DENY",
                        "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
                        "Cache-Control": "no-store"})
        if resp.headers.get("content-type", "").startswith("text/html"):
            body = b"".join([c async for c in resp.body_iterator])
            headers.pop("content-length", None)
            return Response(harden_html(body.decode("utf-8")), status_code=resp.status_code,
                            headers=headers, media_type="text/html")
        for k, v in headers.items():
            resp.headers[k] = v
        return resp

    demo = build_app(service)
    demo.queue(default_concurrency_limit=4)
    theme = gr.themes.Default(font=["system-ui", "Segoe UI", "Arial", "sans-serif"],
                              font_mono=["ui-monospace", "Consolas", "monospace"])
    return gr.mount_gradio_app(api, demo, path="/", theme=theme, css=render.CSS,
                                show_error=False)  # never send exception text to the browser


class RunningServer:
    def __init__(self, server, thread, port: int, host: str = '127.0.0.1') -> None:
        self._server, self._thread, self.port = server, thread, port
        self.url = f"http://{host}:{port}"

    def close(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=10)


def serve(service: DemoService, *, port: int = 7860, background: bool = True, host: str = "127.0.0.1"):
    """Serve on 127.0.0.1 only. background=True returns a handle (used by tests); False blocks."""
    import threading
    import time

    import uvicorn

    check_host(host)
    app = build_server_app(service)
    cfg = uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(cfg)
    if not background:
        server.run()
        return None
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("demo server did not start")
    return RunningServer(server, thread, port, host)

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--semantic", action="store_true", help="use the local multilingual model if present")
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--host", default="127.0.0.1",
                    help="default 127.0.0.1; anything else needs CLAIMS_ALLOW_NONLOOPBACK=1 (no authentication!)")
    ap.add_argument("--tamper-evident", action="store_true",
                    help="with --audit-log: write a hash-chained log (verify: python -m claims_engine.audit_chain verify FILE)")
    ap.add_argument("--audit-log", type=str, default=None, help="append audit events to this JSONL file")
    ap.add_argument("--no-adversarial", action="store_true", help="hide the poisoned test document")
    a = ap.parse_args()
    from pathlib import Path

    check_host(a.host)
    service = DemoService.build(semantic=a.semantic, include_adversarial=not a.no_adversarial,
                                audit_log=Path(a.audit_log) if a.audit_log else None,
                                tamper_evident=a.tamper_evident)
    print(f"Mode: {service.mode} | abstain policy: {service.policy_version} | "
          f"http://{a.host}:{a.port}  (Ctrl+C to stop)")
    serve(service, port=a.port, background=False, host=a.host)


if __name__ == "__main__":
    main()
