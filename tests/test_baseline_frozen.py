"""The M1/M2 baseline is history: M3 must never rewrite it to look better."""
import hashlib
import json
from pathlib import Path

import pytest

from claims_engine.bm25 import analyze
from claims_engine.eval_retrieval import build_corpus, load_cases, run_arm
from claims_engine.retrieval import ChunkIndex

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "eval" / "baseline_m2"


def sums():
    out = {}
    for line in (BASE / "SHA256SUMS").read_text("ascii").splitlines():
        digest, name = line.split(None, 1)
        out[name.strip()] = digest
    return out


@pytest.mark.parametrize("name", ["RETRIEVAL_REPORT.md", "retrieval_results.json", "retrieval_cases.jsonl"])
def test_baseline_files_unchanged(name):
    assert hashlib.sha256((BASE / name).read_bytes()).hexdigest() == sums()[name]


def test_live_m2_case_file_still_equals_frozen_copy():
    assert (ROOT / "eval" / "retrieval_cases.jsonl").read_bytes() == (BASE / "retrieval_cases.jsonl").read_bytes()


def test_frozen_headline_numbers_are_the_published_ones():
    data = json.loads((BASE / "retrieval_results.json").read_text("utf-8"))
    arms = {a["arm"]: a["overall"] for a in data["arms"]}
    assert arms["hybrid RRF"]["recall@5"] == pytest.approx(0.939, abs=1e-3)
    assert arms["bm25 (multilingual)"]["recall@5"] == pytest.approx(0.837, abs=1e-3)
    assert arms["vector"]["recall@5"] == pytest.approx(0.867, abs=1e-3)


def test_m2_lexical_arm_reproduces_exactly_with_m3_code(tmp_path):
    """Running the UNCHANGED M2 code path with the M2 analyzer must give the frozen BM25 numbers."""
    chunks, ids = build_corpus(ROOT / "data" / "policies")
    cases = load_cases(BASE / "retrieval_cases.jsonl")
    arm = run_arm("bm25", ChunkIndex(chunks, analyzer=analyze), "bm25", cases, ids)
    frozen = {a["arm"]: a for a in json.loads((BASE / "retrieval_results.json").read_text("utf-8"))["arms"]}
    old = frozen["bm25 (multilingual)"]["overall"]
    for k in ("recall@1", "recall@3", "recall@5", "hit@5", "MRR", "n"):
        assert arm["overall"][k] == pytest.approx(old[k], abs=1e-9)


def test_original_synthetic_policies_are_byte_identical_to_m2(tmp_path):
    from claims_engine.synthetic import generate_all

    fresh = {p.name: p.read_bytes() for p in generate_all(tmp_path)}
    for name, data in fresh.items():
        assert (ROOT / "data" / "policies" / name).read_bytes() == data