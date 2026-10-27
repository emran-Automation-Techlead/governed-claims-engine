"""Deterministic, offline, rule-based assessor (baseline). No model calls, no network.

It reads clause text with a small EN/FR/DE cue lexicon and applies explicit rules. It does NOT
understand a claim: it only labels what the retrieved clauses say and refuses to decide when
they conflict, contain exceptions, or do not speak to coverage at all. Every output is a
preliminary interpretation for a human reviewer, never a claim decision.

Rules (primary evidence = supported chunks among the top `window` retrieved):
  * exception/reinstatement language, or a clause mixing grant + restriction  -> human_review
  * both a coverage clause and an exclusion clause supported in the window     -> human_review
  * only exclusion clause(s)                                                   -> potentially_excluded
  * only coverage clause(s)                                                    -> potentially_covered
  * only definitions / limits / procedures                                     -> human_review
Conditions found in the cited clause ("unless", "only if", "sauf", "nur wenn", ...) are surfaced
as missing_information for the reviewer to verify; the scenario facts are never assumed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .bm25 import fold
from .schemas import Assessment, AssessmentStatus, Chunk, EvidenceRef
from .support import ScoredChunk

NAME, VERSION = "rules", "1.0.0"
WINDOW = 3
MAX_CITED = 3


class Kind(str, Enum):
    COVERAGE = "coverage"
    EXCLUSION = "exclusion"
    EXCEPTION = "exception"
    MIXED = "mixed"
    DEFINITION = "definition"
    NEUTRAL = "neutral"


def _rx(*alts: str) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(alts) + r")\b", re.IGNORECASE)


_EXCLUSION = _rx(
    r"(?:we|will)\s+(?:do\s+)?not\s+(?:cover|pay|reimburse|insure)", r"does\s+not\s+cover",
    r"(?:is|are)\s+(?:not\s+covered|excluded|not\s+insured)", r"cover\w*\b[^.]{0,60}\b(?:suspended)",
    r"no\s+cover", r"excludes?\b", r"not\s+(?:a\s+valid|covered)",
    r"ne\s+(?:couvrons|garantissons|remboursons)\s+pas", r"sont\s+exclus", r"(?:est|sont)\s+exclue?s?",
    r"n.?est\s+pas\s+(?:garanti|couvert)", r"garantie\b[^.]{0,60}\bsuspendue",
    r"nicht\s+versichert", r"ausgeschlossen", r"kein\s+versicherungsschutz",
    r"schutz\s+ruht", r"ruht\b", r"nicht\s+erstattet",
)
_COVERAGE = _rx(
    r"we\s+cover", r"(?:is|are)\s+covered", r"cover\s+for", r"we\s+pay", r"we\s+reimburse",
    r"nous\s+(?:garantissons|remboursons|couvrons|versons)", r"(?:est|sont)\s+garantie?s?",
    r"wir\s+(?:ersetzen|erstatten|ue?bernehmen|zahlen)", r"(?:ersetzen|erstatten|ue?bernehmen|zahlen)\s+wir", r"(?:ist|sind)\s+versichert", r"versichert\s+ist",
    r"versichert",  # any "versichert" left after "nicht versichert" was removed
)
_EXCEPTION = _rx(
    r"(?:does|do|shall)\s+not\s+apply", r"notwithstanding", r"by\s+way\s+of\s+exception",
    r"ne\s+s.?applique(?:nt)?\s+pas", r"par\s+derogation", r"gilt\s+nicht", r"finden?\s+keine\s+anwendung",
    r"ausnahme",
)
_CONDITION = _rx(
    r"unless", r"only\s+if", r"only\s+when", r"provided\s+that", r"subject\s+to", r"except",
    r"if\b", r"sauf", r"uniquement", r"seulement", r"a\s+condition", r"si\b",
    r"nur\b", r"es\s+sei\s+denn", r"ausser", r"sofern", r"wenn",
)
_DEFINITION_SECTIONS = {"definitions", "definition", "begriffe", "begriffsbestimmungen"}


def joined(e: ScoredChunk) -> Chunk:
    """The chunk with the text of its same-clause continuations appended (condition may follow)."""
    if not e.continuation:
        return e.chunk
    return e.chunk.model_copy(update={"text": " ".join([e.chunk.text, *(c.text for c in e.continuation)])})


def classify(chunk: Chunk) -> Kind:
    if fold(chunk.section_title or "") in _DEFINITION_SECTIONS:
        return Kind.DEFINITION
    t = fold(chunk.text)
    if _EXCEPTION.search(t):
        return Kind.EXCEPTION
    has_ex = bool(_EXCLUSION.search(t))
    rest = _EXCLUSION.sub(" ", t)
    has_cov = bool(_COVERAGE.search(rest))
    if has_ex and has_cov:
        return Kind.MIXED
    if has_ex:
        return Kind.EXCLUSION
    if has_cov:
        return Kind.COVERAGE
    return Kind.NEUTRAL


def condition_sentence(chunk: Chunk) -> str | None:
    for s in re.split(r"(?<=[.;])\s+", chunk.text):
        if _CONDITION.search(fold(s)):
            return s[:200]
    return None


@dataclass(frozen=True)
class AssessmentInput:
    query: str
    evidence: tuple[ScoredChunk, ...]  # in retrieval order, in scope, not quarantined


class Assessor(Protocol):
    name: str
    version: str

    def assess(self, inp: AssessmentInput, attempt: int) -> Assessment: ...


class RuleAssessor:
    name, version = NAME, VERSION

    def assess(self, inp: AssessmentInput, attempt: int = 0) -> Assessment:
        window = [e for e in inp.evidence[:WINDOW] if e.supported]
        kinds = [(e, classify(joined(e))) for e in window]
        real = [(e, k) for e, k in kinds if k != Kind.DEFINITION] or kinds
        present = {k for _, k in real}

        def ref(e: ScoredChunk) -> EvidenceRef:
            return e.chunk.to_evidence(score=e.hit.score)

        def refs(es) -> tuple[EvidenceRef, ...]:
            out: list[EvidenceRef] = []
            for e in es:
                out.append(ref(e))
                out.extend(c.to_evidence() for c in e.continuation)  # keep the cited clause whole
            return tuple(out)

        def build(status: AssessmentStatus, summary: str, **kw) -> Assessment:
            return Assessment(status=status, summary=summary, model_version=f"{NAME}-{VERSION}",
                              prompt_version="n/a-deterministic", **kw)

        if not real:
            return build(AssessmentStatus.INSUFFICIENT_EVIDENCE, "No supported clause.",
                         missing_information=("a clause that addresses the described loss",))
        if present & {Kind.EXCEPTION, Kind.MIXED}:
            bad = next(e for e, k in real if k in (Kind.EXCEPTION, Kind.MIXED))
            return build(AssessmentStatus.HUMAN_REVIEW_REQUIRED,
                         "Relevant clause contains an exception or both a grant and a restriction.",
                         escalation_reason=(f"clause {bad.chunk.clause_id} (p.{bad.chunk.page_number}) "
                                            "has exception/reinstatement or mixed grant-and-restriction wording"),
                         exclusions_and_limitations=refs([bad]),
                         uncertainty="Rule-based reading cannot resolve exception wording.")
        if {Kind.COVERAGE, Kind.EXCLUSION} <= present:
            cov = next(e for e, k in real if k == Kind.COVERAGE)
            exc = next(e for e, k in real if k == Kind.EXCLUSION)
            return build(AssessmentStatus.HUMAN_REVIEW_REQUIRED,
                         "Competing clauses: one grants cover, another excludes or limits it.",
                         escalation_reason=(f"conflict between coverage clause {cov.chunk.clause_id} "
                                            f"(p.{cov.chunk.page_number}) and exclusion clause "
                                            f"{exc.chunk.clause_id} (p.{exc.chunk.page_number})"),
                         supporting_clauses=refs([cov]), exclusions_and_limitations=refs([exc]),
                         uncertainty="Both clauses may apply depending on facts not yet verified.")
        picked = [e for e, k in real][:MAX_CITED]
        conds = tuple(
            f"Verify condition in clause {e.chunk.clause_id}: {c}" for e in picked
            if (c := condition_sentence(joined(e))))
        note = "Preliminary clause-level reading; scenario facts are not verified."
        if present == {Kind.EXCLUSION}:
            return build(AssessmentStatus.POTENTIALLY_EXCLUDED,
                         "The most relevant clause(s) appear to exclude or limit this loss.",
                         exclusions_and_limitations=refs(picked),
                         missing_information=conds, uncertainty=note)
        if present == {Kind.COVERAGE}:
            return build(AssessmentStatus.POTENTIALLY_COVERED,
                         "The most relevant clause(s) appear to grant cover for this loss.",
                         supporting_clauses=refs(picked),
                         missing_information=conds, uncertainty=note)
        first = real[0][0]
        return build(AssessmentStatus.HUMAN_REVIEW_REQUIRED,
                     "Relevant clauses are definitions, limits or procedures, not a grant or exclusion.",
                     escalation_reason=(f"clause {first.chunk.clause_id} (p.{first.chunk.page_number}) "
                                        "does not itself grant or exclude cover"),
                     uncertainty=note)