r"""Optional tamper-EVIDENT audit log: a SHA-256 hash chain over JSON lines.

Each line: {"seq": n, "prev": <hash of previous line or 64 zeros>, "event": {...}, "hash": sha256(f"{seq}|{prev}|{canonical(event)}")}.
`verify_chain` detects: edited events, edited/reordered/deleted lines in the MIDDLE, wrong sequence numbers.
It does NOT detect (documented limits, not solved here):
  * truncation of the END of the log, or replacing the whole file with a freshly forged valid chain,
    unless the latest `head` hash was copied somewhere the attacker cannot write (write-once store, separate account);
  * a writer that is itself malicious (it can append false events);
  * confidentiality: events are plain text.
Production would anchor the head hash externally (e.g. object lock / ledger / signed timestamps) and use
access-controlled storage. Run:  python -m claims_engine.audit_chain verify <file>
"""
from __future__ import annotations

import hashlib
import json
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

GENESIS = "0" * 64


def _canonical(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _link(seq: int, prev: str, event: dict) -> str:
    return hashlib.sha256(f"{seq}|{prev}|{_canonical(event)}".encode()).hexdigest()


@dataclass(frozen=True)
class ChainResult:
    ok: bool
    lines: int
    head: str
    error: str | None = None


def verify_chain(path: Path | str) -> ChainResult:
    p = Path(path)
    prev, n = GENESIS, 0
    if not p.exists():
        return ChainResult(False, 0, GENESIS, "file does not exist")
    for n, raw in enumerate(p.read_text("utf-8").splitlines(), start=1):
        try:
            rec = json.loads(raw)
            seq, rprev, event, rhash = rec["seq"], rec["prev"], rec["event"], rec["hash"]
        except (ValueError, KeyError, TypeError):
            return ChainResult(False, n, prev, f"line {n}: malformed record")
        if seq != n:
            return ChainResult(False, n, prev, f"line {n}: sequence number {seq} (line deleted or reordered?)")
        if rprev != prev:
            return ChainResult(False, n, prev, f"line {n}: previous-hash mismatch (line removed or changed before it)")
        if _link(seq, prev, event) != rhash:
            return ChainResult(False, n, prev, f"line {n}: event does not match its hash (edited)")
        prev = rhash
    return ChainResult(True, n if p.stat().st_size else 0, prev)


class ChainedJsonlSink:
    """AuditSink that appends hash-chained lines; resumes an existing, valid chain."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size:
            res = verify_chain(self.path)
            if not res.ok:
                raise ValueError(f"refusing to append to a broken audit chain: {res.error}")
            self._prev, self._n = res.head, res.lines
        else:
            self._prev, self._n = GENESIS, 0

    @property
    def head(self) -> str:
        return self._prev

    def write(self, event: dict) -> None:
        with self._lock:
            self._n += 1
            h = _link(self._n, self._prev, event)
            line = {"seq": self._n, "prev": self._prev, "event": event, "hash": h}
            with self.path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(line, ensure_ascii=False, sort_keys=True, default=str) + "\n")
            self._prev = h


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] != "verify":
        print("usage: python -m claims_engine.audit_chain verify <file>")
        return 2
    r = verify_chain(argv[1])
    print(("OK" if r.ok else "BROKEN") + f": {r.lines} line(s), head={r.head}" + (f", {r.error}" if r.error else ""))
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())