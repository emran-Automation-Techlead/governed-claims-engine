"""Generated evaluation/calibration artifacts must be written with LF line endings on every platform.

On Windows ``Path.write_text`` translates ``\\n`` to ``\\r\\n`` unless ``newline`` is given, which silently changes the bytes of
frozen, hash-checked files (found when ``calibrate`` rewrote ``abstain_policy.json`` with CRLF).
"""
import ast
import sys
from pathlib import Path

import pytest

from claims_engine import eval_retrieval

SRC = Path(__file__).resolve().parents[1] / "src" / "claims_engine"
WRITERS = ["calibrate", "eval_variants", "eval_workflow", "eval_retrieval"]


def _write_text_calls(module: str):
    tree = ast.parse((SRC / f"{module}.py").read_text("utf-8"))
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "write_text"]


@pytest.mark.parametrize("module", WRITERS)
def test_every_artifact_writer_pins_lf_newlines(module):
    calls = _write_text_calls(module)
    assert calls, f"{module} no longer writes artifacts; update this guard"
    for call in calls:
        kw = {k.arg: k.value for k in call.keywords}
        assert isinstance(kw.get("newline"), ast.Constant) and kw["newline"].value == "\n", (
            f"{module}.py line {call.lineno}: write_text must pass newline='\\n'")
        assert isinstance(kw.get("encoding"), ast.Constant) and kw["encoding"].value == "utf-8"


def test_retrieval_report_bytes_have_no_carriage_returns(tmp_path, monkeypatch, all_policies):
    policies = next(iter(all_policies.values())).parent
    cases = Path(__file__).resolve().parents[1] / "eval" / "retrieval_cases.jsonl"
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["eval_retrieval", "--no-semantic", "--policies", str(policies),
                                      "--cases", str(cases), "--out", str(out)])
    eval_retrieval.main()
    for rel in ("RETRIEVAL_REPORT.md", "results/retrieval_results.json"):
        data = (out / rel).read_bytes()
        assert data and b"\r" not in data, rel
        assert data.endswith(b"\n") or rel.endswith(".json")
