import json
import threading

import pytest

from claims_engine.audit_chain import GENESIS, ChainedJsonlSink, main, verify_chain
from claims_engine.demo_service import DemoService


def events(n=5):
    return [{"event": "assessment", "trace_id": f"t{i}", "status": "potentially_covered"} for i in range(n)]


def write(path, evs=None):
    sink = ChainedJsonlSink(path)
    for e in evs or events():
        sink.write(e)
    return sink


def test_empty_and_missing_files(tmp_path):
    assert verify_chain(tmp_path / "none.jsonl").ok is False
    (tmp_path / "empty.jsonl").write_text("", "utf-8")
    r = verify_chain(tmp_path / "empty.jsonl")
    assert r.ok and r.lines == 0 and r.head == GENESIS


def test_valid_chain_verifies_and_head_matches_the_sink(tmp_path):
    sink = write(tmp_path / "a.jsonl")
    r = verify_chain(tmp_path / "a.jsonl")
    assert r.ok and r.lines == 5 and r.head == sink.head != GENESIS


def test_each_line_links_to_the_previous_one(tmp_path):
    write(tmp_path / "a.jsonl")
    recs = [json.loads(x) for x in (tmp_path / "a.jsonl").read_text("utf-8").splitlines()]
    assert recs[0]["prev"] == GENESIS and [r["seq"] for r in recs] == [1, 2, 3, 4, 5]
    assert all(recs[i]["prev"] == recs[i - 1]["hash"] for i in range(1, 5))


def tamper(path, fn):
    lines = path.read_text("utf-8").splitlines()
    out = fn(lines)
    path.write_text("\n".join(out) + "\n", "utf-8")


def test_editing_an_event_is_detected(tmp_path):
    p = tmp_path / "a.jsonl"
    write(p)
    tamper(p, lambda ls: [ls[0], ls[1].replace("potentially_covered", "potentially_excluded"), *ls[2:]])
    r = verify_chain(p)
    assert not r.ok and "line 2" in r.error and "edited" in r.error


def test_deleting_a_middle_line_is_detected(tmp_path):
    p = tmp_path / "a.jsonl"
    write(p)
    tamper(p, lambda ls: [ls[0], ls[1], ls[3], ls[4]])
    r = verify_chain(p)
    assert not r.ok and "line 3" in r.error


def test_reordering_is_detected(tmp_path):
    p = tmp_path / "a.jsonl"
    write(p)
    tamper(p, lambda ls: [ls[1], ls[0], *ls[2:]])
    assert not verify_chain(p).ok


def test_garbage_line_is_detected(tmp_path):
    p = tmp_path / "a.jsonl"
    write(p)
    tamper(p, lambda ls: [*ls, "not json"])
    assert "malformed" in verify_chain(p).error


def test_rewriting_hash_of_an_edited_line_still_breaks_the_next_link(tmp_path):
    import hashlib

    p = tmp_path / "a.jsonl"
    write(p)
    recs = [json.loads(x) for x in p.read_text("utf-8").splitlines()]
    recs[1]["event"]["status"] = "forged"
    canon = json.dumps(recs[1]["event"], ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    recs[1]["hash"] = hashlib.sha256(f"{recs[1]['seq']}|{recs[1]['prev']}|{canon}".encode()).hexdigest()  # attacker fixes line 2's hash
    p.write_text("\n".join(json.dumps(r, sort_keys=True) for r in recs) + "\n", "utf-8")
    r = verify_chain(p)
    assert not r.ok and "line 3" in r.error  # ...but line 3 still points at the old hash


def edit_field(path, line_no, field, value):
    recs = [json.loads(x) for x in path.read_text("utf-8").splitlines()]
    recs[line_no - 1][field] = value
    path.write_text("\n".join(json.dumps(r, sort_keys=True) for r in recs) + "\n", "utf-8")


def test_forging_only_the_stored_prev_field_is_detected(tmp_path):
    p = tmp_path / "a.jsonl"
    write(p)
    edit_field(p, 3, "prev", "f" * 64)
    r = verify_chain(p)
    assert not r.ok and "line 3" in r.error


def test_editing_only_the_sequence_number_is_detected(tmp_path):
    p = tmp_path / "a.jsonl"
    write(p)
    edit_field(p, 4, "seq", 99)
    r = verify_chain(p)
    assert not r.ok and "line 4" in r.error


def test_documented_limit_tail_truncation_is_NOT_detected_without_an_external_anchor(tmp_path):
    p = tmp_path / "a.jsonl"
    sink = write(p)
    anchored_head = sink.head
    tamper(p, lambda ls: ls[:3])  # attacker drops the last two events
    r = verify_chain(p)
    assert r.ok  # a valid shorter chain: this is the honest limitation
    assert r.head != anchored_head  # only an externally stored head hash reveals it


def test_sink_resumes_a_valid_chain_and_refuses_a_broken_one(tmp_path):
    p = tmp_path / "a.jsonl"
    write(p, events(3))
    ChainedJsonlSink(p).write({"event": "later"})
    assert verify_chain(p).lines == 4
    tamper(p, lambda ls: [ls[0].replace("t0", "tX"), *ls[1:]])
    with pytest.raises(ValueError, match="broken audit chain"):
        ChainedJsonlSink(p)


def test_concurrent_writers_keep_the_chain_intact(tmp_path):
    p = tmp_path / "a.jsonl"
    sink = ChainedJsonlSink(p)
    ts = [threading.Thread(target=lambda i=i: [sink.write({"w": i, "n": n}) for n in range(20)]) for i in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    r = verify_chain(p)
    assert r.ok and r.lines == 120


def test_cli_exit_codes(tmp_path, capsys):
    p = tmp_path / "a.jsonl"
    write(p)
    assert main(["verify", str(p)]) == 0 and "OK: 5 line(s)" in capsys.readouterr().out
    tamper(p, lambda ls: [ls[0], ls[2]])
    assert main(["verify", str(p)]) == 1 and "BROKEN" in capsys.readouterr().out
    assert main([]) == 2


def test_demo_service_can_write_a_tamper_evident_log_without_question_text(tmp_path):
    s = DemoService.build(include_adversarial=False, audit_log=tmp_path / "audit.jsonl", tamper_evident=True)
    d = s.documents()[0].doc_id
    r = s.assess("my private story burst pipes sudden accidental escape water", [d])
    s.review(r.result.trace_id, "reviewer-1", "approve", None, None)
    res = verify_chain(tmp_path / "audit.jsonl")
    assert res.ok and res.lines == 2
    assert "private story" not in (tmp_path / "audit.jsonl").read_text("utf-8")