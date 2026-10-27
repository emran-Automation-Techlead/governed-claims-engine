"""Gradio callbacks (called directly) and the real running app (live server + independent client sessions)."""
import os
import re
import socket
import urllib.error
import urllib.request

import pytest

from claims_engine import render
from claims_engine.app import CSP, build_app, harden_html, make_handlers, serve
from claims_engine.demo_service import EXAMPLES, DemoService

HOME, TRAVEL = "synthetic_home_policy.pdf", "synthetic_travel_policy.pdf"
QUESTION = "burst pipes sudden accidental escape water"


@pytest.fixture(scope="module")
def svc():
    return DemoService.build()


@pytest.fixture(scope="module")
def ids(svc):
    return {d.filename: d.doc_id for d in svc.documents()}


@pytest.fixture(scope="module")
def h(svc):
    return make_handlers(svc)


def val(update_or_value):
    """Gradio update dicts carry the new value under 'value'."""
    return update_or_value.get("value") if isinstance(update_or_value, dict) else update_or_value


# ------------------------------------------------------------------ direct callback tests
def test_assess_callback_returns_all_panels_and_session_state(h, ids):
    out = h["assess"](QUESTION, [ids[HOME]], {})
    status, reasons, evidence, state, proposed, history, review_msg, trace = out
    assert "SUPPORTED PRELIMINARY ASSESSMENT" in status and "Potentially covered" in status
    assert "Clause 3.1 - page 3" in evidence and "Uncertainty" in reasons
    assert re.fullmatch(r"[0-9a-f]{32}", state["trace_id"]) and val(trace) == state["trace_id"]
    assert state["trace_id"] in proposed and "No review recorded" in history and review_msg == ""


def test_each_assess_call_is_independent_of_the_previous_one(h, ids):
    first = h["assess"](QUESTION, [ids[HOME]], {})
    second = h["assess"]("baggage limit single item lost stolen", [ids[TRAVEL]], first[3])  # old state passed in
    assert first[3]["trace_id"] != second[3]["trace_id"]
    assert HOME not in second[2] and TRAVEL in second[2]  # no evidence carried over
    assert first[3]["trace_id"] not in second[0] + second[1] + second[2] + second[4]
    assert "No review recorded" in second[5]  # no review history carried over


@pytest.mark.parametrize("query,docs", [("", [None]), ("   ", None), (QUESTION, []), (QUESTION, None), (None, None),
                                        ("x" * 2001, None)])
def test_assess_callback_survives_invalid_input(h, ids, query, docs):
    if docs == [None] or docs is None and query not in (None, QUESTION):
        docs = [ids[HOME]]
    out = h["assess"](query, docs, {})
    assert "REQUEST REJECTED" in out[0] and out[2].count("ce-card") == 0
    assert "Nothing to review" in out[4]


def test_scope_callback_shows_only_selected_documents(h, ids):
    both = h["scope"]([ids[HOME], ids[TRAVEL]])
    assert HOME in both and TRAVEL in both and "synthetic_motor_policy.pdf" not in both
    assert "none selected" in h["scope"]([]).lower() and "none selected" in h["scope"](None).lower()
    assert "ignored" not in h["scope"](["doc-forged"]).lower()


def test_example_callback_fills_question_and_scope(h, ids):
    label, files, question, _ = EXAMPLES[3]
    q, docs, scope = h["example"](label)
    assert q == question and docs == [ids[f] for f in files] and files[0] in scope
    noop = h["example"]("not an example")
    assert all(isinstance(x, dict) for x in noop)


def test_review_callback_records_override_and_shows_original_beside_outcome(h, svc, ids):
    state = h["assess"](QUESTION, [ids[HOME]], {})[3]
    msg, history, _ = h["review"](state, "reviewer-1", "Override", "potentially_excluded",
                                  "Please check clause 4.3 before relying on this.")
    assert "Demonstration review recorded" in msg and "not a binding decision" in msg
    assert "OVERRIDE" in history and "Potentially covered" in history and "Potentially excluded" in history
    assert "NOT a legally binding insurance decision" in history
    assert svc.get(state["trace_id"]).result.assessment.status.value == "potentially_covered"


def test_review_callback_enforces_explanation_and_reports_errors(h, ids):
    state = h["assess"](QUESTION, [ids[HOME]], {})[3]
    msg, history, _ = h["review"](state, "reviewer-1", "Override", "human_review_required", "")
    assert "Not recorded" in msg and "explanation" in msg.lower() and "No review recorded" in history
    msg2, _, _ = h["review"](state, "reviewer-1", "Override", None, "a perfectly fine explanation")
    assert "Not recorded" in msg2
    msg3, _, _ = h["review"](state, "x@y.org", "Approve", None, "")
    assert "Not recorded" in msg3 and "pseudonym" in msg3
    msg4, _, _ = h["review"](state, "reviewer-1", "Reject", None, "")
    assert "Not recorded" in msg4


def test_review_callback_without_an_assessment_is_a_clear_error(h):
    msg, history, _ = h["review"]({}, "reviewer-1", "Approve", None, "")
    assert "No assessment is selected" in msg and "No review recorded" in history
    msg2, _, _ = h["review"](None, "reviewer-1", "Approve", None, "")
    assert "No assessment is selected" in msg2


def test_two_sessions_cannot_review_each_others_assessments(h, svc, ids):
    s1 = h["assess"](QUESTION, [ids[HOME]], {})[3]
    s2 = h["assess"](QUESTION, [ids[HOME]], {})[3]
    h["review"](s1, "reviewer-1", "Approve", None, "")
    assert len(svc.get(s1["trace_id"]).reviews) == 1 and svc.get(s2["trace_id"]).reviews == []
    h["review"](s2, "reviewer-2", "Override", "human_review_required", "second session's own override")
    assert svc.get(s1["trace_id"]).reviews[0].reviewer_id == "reviewer-1"
    assert svc.get(s2["trace_id"]).reviews[0].reviewer_id == "reviewer-2"


def test_audit_callback_returns_table_and_raw_json(h, ids):
    state = h["assess"](QUESTION, [ids[HOME]], {})[3]
    h["review"](state, "reviewer-1", "Approve", None, "")
    html, raw = h["audit"](state["trace_id"])
    assert state["trace_id"] in html and "Review history" in html and "approve" in html
    assert raw["trace_id"] == state["trace_id"] and raw["question_text_stored"] is False
    empty_html, empty_raw = h["audit"]("unknown")
    assert "Select a trace" in empty_html and empty_raw == {}


def test_refresh_callback_lists_recent_traces_with_current_selected(h, ids):
    state = h["assess"](QUESTION, [ids[HOME]], {})[3]
    upd = h["recent"](state)
    assert upd["value"] == state["trace_id"] and upd["choices"][0][1] == state["trace_id"]


def test_ui_can_be_constructed_and_declares_its_endpoints(svc):
    app = build_app(svc)
    names = {f.api_name for f in app.fns.values()}
    assert {"scope", "example", "assess", "review", "audit", "recent"} <= names


def test_html_hardening_removes_third_party_references():
    page = ('<link rel="preconnect" href="https://fonts.googleapis.com" />\n<link\n rel="preconnect"\n'
            ' href="https://fonts.gstatic.com" crossorigin="anonymous" />\n'
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/iframe-resizer/4.3.1/iframeResizer.contentWindow.min.js"\n></script>'
            '<meta content="https://raw.githubusercontent.com/gradio-app/gradio/main/a.jpg" />ok')
    out = harden_html(page)
    assert "googleapis" not in out and "gstatic" not in out and "cdnjs" not in out and "githubusercontent" not in out
    assert out.endswith('ok')
    assert "connect-src 'self'" in CSP and "frame-ancestors 'none'" in CSP


# ------------------------------------------------------------------ live server, independent client sessions
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live(svc):
    srv = serve(svc, port=_free_port())
    yield srv
    srv.close()


@pytest.fixture(scope="module")
def client_cls():
    from gradio_client import Client

    return Client


def test_live_page_is_local_only_hardened_and_makes_no_third_party_references(live):
    r = urllib.request.urlopen(live.url + "/", timeout=15)
    html = r.read().decode()
    assert r.status == 200 and "Governed Claims Coverage Engine" in html
    assert r.headers["Content-Security-Policy"] == CSP and r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer" and r.headers["X-Content-Type-Options"] == "nosniff"
    external = {u for u in re.findall(r'(?:src|href)="(https?://[^"]+)"', html) if "127.0.0.1" not in u}
    assert external == set(), external
    assert live._server.config.host == "127.0.0.1"


def test_live_end_to_end_assess_review_audit_in_one_session(live, client_cls, svc, ids):
    c = client_cls(live.url, verbose=False)
    out = c.predict(QUESTION, [ids[HOME]], api_name="/assess")
    status, _reasons, evidence, _proposed, _history, _msg, trace = out
    assert "SUPPORTED PRELIMINARY ASSESSMENT" in status and "Clause 3.1 - page 3" in evidence
    tid = trace["value"] if isinstance(trace, dict) else trace
    msg, history, _ = c.predict("reviewer-9", "Override", "human_review_required",
                                "end-to-end override explanation", api_name="/review")
    assert "Demonstration review recorded" in msg and "OVERRIDE" in history
    stored = svc.get(tid)
    assert stored.reviews[0].reviewer_id == "reviewer-9"
    assert stored.result.assessment.status.value == "potentially_covered"  # original preserved
    html, raw = c.predict(tid, api_name="/audit")
    assert raw["review_history"][0]["effective_status"] == "human_review_required" and "reviewer-9" in html

def test_live_two_sessions_are_isolated(live, client_cls, svc, ids):
    a, b = client_cls(live.url, verbose=False), client_cls(live.url, verbose=False)
    oa = a.predict(QUESTION, [ids[HOME]], api_name="/assess")
    ob = b.predict("baggage limit single item lost stolen", [ids[TRAVEL]], api_name="/assess")
    assert HOME in oa[2] and TRAVEL not in oa[2]
    assert TRAVEL in ob[2] and HOME not in ob[2]
    # session A records a review; session B (own state) records its own; neither sees the other's
    ra = a.predict("reviewer-a", "Override", "potentially_excluded", "session A explanation text",
                   api_name="/review")
    rb = b.predict("reviewer-b", "Approve", None, "", api_name="/review")
    assert "Demonstration review recorded" in ra[0] and "Demonstration review recorded" in rb[0]
    assert "reviewer-a" in ra[1] and "reviewer-b" not in ra[1]
    assert "reviewer-b" in rb[1] and "reviewer-a" not in rb[1]


def test_live_review_without_an_assessment_is_refused(live, client_cls):
    fresh_session = client_cls(live.url, verbose=False)
    out = fresh_session.predict("reviewer-1", "Approve", None, "", api_name="/review")
    assert "No assessment is selected" in out[0]


def test_live_invalid_input_returns_a_rejection_not_a_crash(live, client_cls, ids):
    c = client_cls(live.url, verbose=False)
    out = c.predict("", [ids[HOME]], api_name="/assess")
    assert "REQUEST REJECTED" in out[0]
    out2 = c.predict("lorem ipsum dolor sit amet " * 50, [ids[HOME]], api_name="/assess")  # long, unrelated
    assert "INSUFFICIENT EVIDENCE" in out2[0]
    out3 = c.predict("x" * 1500, [ids[HOME]], api_name="/assess")  # looks like an encoded blob
    assert "HUMAN REVIEW REQUIRED" in out3[0]


def test_live_audit_endpoint_returns_the_record(live, client_cls, ids, svc):
    c = client_cls(live.url, verbose=False)
    out = c.predict(QUESTION, [ids[HOME]], api_name="/assess")
    trace = out[-1]
    tid = trace["value"] if isinstance(trace, dict) else trace
    html, raw = c.predict(tid, api_name="/audit")
    assert tid in html and raw["documents"][0]["filename"] == HOME and raw["question_text_stored"] is False
    assert svc.doc(ids[HOME]).sha256 in html


def test_live_server_works_with_the_network_blocked(live, client_cls, ids, monkeypatch):
    real = socket.socket.connect

    def only_loopback(self, address, *a, **k):
        host = address[0] if isinstance(address, tuple) else address
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise AssertionError(f"non-loopback connection attempted: {address}")
        return real(self, address, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", only_loopback)
    c = client_cls(live.url, verbose=False)
    assert "SUPPORTED" in c.predict(QUESTION, [ids[HOME]], api_name="/assess")[0]
    assert render  # imported for completeness

# ------------------------------------------------------------------ M5: host guard and health endpoint
@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_loopback_hosts_are_always_allowed(host, monkeypatch):
    from claims_engine.app import check_host

    monkeypatch.delenv("CLAIMS_ALLOW_NONLOOPBACK", raising=False)
    check_host(host)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "example.com", "::", ""])
def test_non_loopback_binding_is_refused_without_explicit_opt_in(host, monkeypatch):
    from claims_engine.app import check_host

    monkeypatch.delenv("CLAIMS_ALLOW_NONLOOPBACK", raising=False)
    with pytest.raises(SystemExit, match="no authentication"):
        check_host(host)
    monkeypatch.setenv("CLAIMS_ALLOW_NONLOOPBACK", "0")
    with pytest.raises(SystemExit):
        check_host(host)  # only the exact value "1" opts in
    monkeypatch.setenv("CLAIMS_ALLOW_NONLOOPBACK", "1")
    check_host(host)


def test_serve_and_cli_honour_the_host_guard(svc, monkeypatch):
    import sys

    from claims_engine import app as app_mod

    monkeypatch.delenv("CLAIMS_ALLOW_NONLOOPBACK", raising=False)
    with pytest.raises(SystemExit):
        app_mod.serve(svc, port=_free_port(), host="0.0.0.0")
    monkeypatch.setattr(sys, "argv", ["x", "--host", "0.0.0.0"])
    with pytest.raises(SystemExit):
        app_mod.main()


def test_default_binding_is_loopback_in_code_and_cli():
    import inspect

    from claims_engine import app as app_mod

    assert inspect.signature(app_mod.serve).parameters["host"].default == "127.0.0.1"
    assert "default=\"127.0.0.1\"" in inspect.getsource(app_mod.main)


def test_healthz_is_a_minimal_liveness_probe_with_security_headers(live):
    import json

    r = urllib.request.urlopen(live.url + "/healthz", timeout=10)
    assert r.status == 200 and json.loads(r.read()) == {"status": "ok"}
    assert r.headers["Content-Security-Policy"] == CSP and r.headers["Cache-Control"] == "no-store"


def test_no_swagger_ui_but_gradio_schema_endpoints_exist_and_leak_no_local_paths(live):
    """Documented behaviour: Gradio itself serves its component config / API schema (/config, /gradio_api/info,
    /openapi.json). They must not contain local filesystem paths or the OS user name; in production they belong
    behind authentication (governance/GRADIO_SECURITY_REVIEW.md)."""
    for path in ("/docs", "/redoc"):
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(live.url + path, timeout=10)
        assert e.value.code == 404
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "zzz-no-user"
    for path in ("/", "/config", "/gradio_api/info", "/openapi.json", "/gradio_api/openapi.json"):
        body = urllib.request.urlopen(live.url + path, timeout=10).read().decode("utf-8", "replace")
        assert user.lower() not in body.lower(), path
        assert not re.search(r"[A-Za-z]:\\\\|/home/|/Users/|AppData", body), path
        assert "question_text" not in body.lower()

# ------------------------------------------------------------------ M5: error handling and documented cross-session audit view
def test_unexpected_server_errors_do_not_leak_exception_text_to_the_client(client_cls):
    class Exploding(DemoService):
        def assess(self, query, doc_ids):  # simulate an unexpected internal failure
            raise RuntimeError("INTERNAL-SECRET-DETAIL /srv/app/secret.py line 42")

    base = DemoService.build(include_adversarial=False)
    broken = Exploding(base.workflow, base.documents(), sink=base.sink, mode=base.mode)
    assert build_app(broken) is not None
    srv = serve(broken, port=_free_port())
    try:
        c = client_cls(srv.url, verbose=False)
        with pytest.raises(Exception) as exc:
            c.predict(QUESTION, [broken.documents()[0].doc_id], api_name="/assess")
        text = str(exc.value) + repr(exc.value.args)
        assert "INTERNAL-SECRET-DETAIL" not in text and "secret.py" not in text
    finally:
        srv.close()


def test_server_is_mounted_with_show_error_disabled(svc):
    from claims_engine.app import build_server_app

    api = build_server_app(svc)
    blocks = [r.app.blocks for r in api.routes if getattr(getattr(r, "app", None), "blocks", None) is not None]
    assert blocks and all(b.show_error is False for b in blocks)


def test_audit_listing_is_global_across_sessions_documented_limitation(svc, ids):
    """KNOWN LIMITATION (documented in governance/GRADIO_SECURITY_REVIEW.md): the audit tab lists recent traces of ALL
    sessions of this process and shows their audit metadata and review reasons. Fine for a single-operator local demo;
    unacceptable for multi-user use without authentication + per-user trace ownership. This test pins the behaviour so a
    future fix must update the document too."""
    a = svc.assess(QUESTION, [ids[HOME]]).result.trace_id
    b = svc.assess(QUESTION, [ids[TRAVEL]]).result.trace_id
    listed = {t for _, t in svc.recent(200)}
    assert {a, b} <= listed
    assert svc.audit(a)["trace_id"] == a and svc.audit(b)["trace_id"] == b

# ------------------------------------------------------------------ M5: Pillow compensating controls
def _http(url, method="GET", data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_ui_contains_no_component_that_decodes_images_or_accepts_files(svc):
    """The Pillow risk assessment (governance/PILLOW_ADVISORY_REVIEW.md) depends on this: if an image/file/media component
    is ever added, this test fails and the assessment must be redone."""
    forbidden = {"Image", "ImageEditor", "ImageSlider", "AnnotatedImage", "Gallery", "File", "UploadButton", "Video",
                 "Audio", "Model3D", "MultimodalTextbox", "Chatbot", "FileExplorer", "Sketchpad", "Paint", "DownloadButton",
                 "Dataframe", "Plot", "LinePlot", "BarPlot", "ScatterPlot", "ParamViewer"}
    types = {type(b).__name__ for b in build_app(svc).blocks.values()}
    assert not (types & forbidden), types & forbidden


def test_upload_and_file_serving_routes_are_blocked(live):
    boundary = "----b" + "0" * 16
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="x.png"\r\n'
            f"Content-Type: image/png\r\n\r\nNOTANIMAGE\r\n--{boundary}--\r\n").encode()
    hdr = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    for path in ("/gradio_api/upload", "/upload", "/GRADIO_API/UPLOAD"):
        status, text = _http(live.url + path, "POST", body, hdr)
        assert status == 404 and b"disabled" in text, path
    for path in ("/gradio_api/file=/etc/hosts", "/file=/etc/hosts", "/gradio_api/file/abc", "/pwa_icon", "/pwa_icon/64",
                 "/gradio_api/pwa_icon/64", "/gradio_api/resource/x"):
        assert _http(live.url + path)[0] == 404, path


def test_blocked_routes_keep_security_headers_and_do_not_break_the_app(live, client_cls, ids):
    _, _ = _http(live.url + "/gradio_api/upload", "POST", b"x", {"Content-Type": "application/octet-stream"})
    r = urllib.request.Request(live.url + "/upload", method="POST", data=b"x")
    try:
        urllib.request.urlopen(r, timeout=10)
    except urllib.error.HTTPError as e:
        assert e.headers["Content-Security-Policy"] == CSP and e.headers["Cache-Control"] == "no-store"
    assert "SUPPORTED" in client_cls(live.url, verbose=False).predict(QUESTION, [ids[HOME]], api_name="/assess")[0]


def test_blocked_uploads_leave_nothing_in_the_gradio_cache(live):
    import tempfile
    from pathlib import Path

    roots = [Path(os.environ.get("GRADIO_TEMP_DIR") or Path(tempfile.gettempdir()) / "gradio")]
    import uuid

    marker = "PILLOW-UPLOAD-MARKER-" + uuid.uuid4().hex  # unique per run: stale files cannot cause false failures
    boundary = "----c" + "1" * 16
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{marker}.png"\r\n'
            f"Content-Type: image/png\r\n\r\n{marker}\r\n--{boundary}--\r\n").encode()
    _http(live.url + "/gradio_api/upload", "POST", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    for root in roots:
        if root.exists():
            assert not [p for p in root.rglob("*") if marker in p.name]
            assert not [p for p in root.rglob("*") if p.is_file() and p.stat().st_size < 4096
                        and marker.encode() in p.read_bytes()]
