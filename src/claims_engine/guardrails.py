"""Prompt-injection screening - DEFENCE IN DEPTH, NOT A SECURITY BOUNDARY.

What this is: a heuristic detector for instruction-like and obfuscated content in (a) the
user's request and (b) retrieved policy text. Matches are quarantined/escalated to a human.

What this is NOT: a guarantee. Keyword/regex screening is trivially bypassable (paraphrase,
other languages, typos, encodings, splitting across lines). Never rely on it alone.
The primary protections are architectural:
  1. policy text is DATA: the deterministic assessor never interprets text as instructions;
  2. outputs are schema-validated and every citation is checked against retrieved evidence;
  3. document scope is enforced in retrieval and re-checked after it;
  4. unsupported or suspicious cases abstain and go to a human.
If an LLM is added later it must receive evidence as delimited data, with no tools, and its
output must pass the same validators - the screen would remain only a tripwire.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .bm25 import fold

_HIDDEN = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\u00ad]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Patterns run on accent-folded, lower-cased text (so they are written without accents).
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(rx, re.IGNORECASE | re.MULTILINE)) for name, rx in (
        ("override_instructions_en",
         r"\b(ignore|disregard|forget|override|bypass)\b.{0,30}\b(previous|prior|above|earlier|all|"
         r"any|your|the)\b.{0,20}\b(instructions?|rules?|guidelines?|prompts?|safeguards?|policy)\b"),
        ("override_instructions_fr",
         r"\b(ignore[zr]?|oublie[zr]?|ne tenez pas compte)\b.{0,30}\b(instructions?|consignes?|regles?)\b"),
        ("override_instructions_de",
         r"\b(ignorier\w*|vergiss\w*|missachte\w*)\b.{0,30}\b(anweisungen|instruktionen|regeln|vorgaben)\b"),
        ("role_reassignment",
         r"\b(you are now|you are no longer|act as|pretend (to be|you are)|tu es maintenant|"
         r"vous etes maintenant|du bist jetzt|sie sind jetzt)\b"),
        ("system_prompt_reference",
         r"\b(system prompt|developer mode|jailbreak|systemprompt|system-prompt|prompt systeme|"
         r"invite systeme)\b"),
        ("new_instructions", r"\b(new|updated|additional) instructions?\b"),
        ("role_marker", r"^\s*(system|assistant|developer|admin)\s*:"),
        ("chat_template_marker", r"(<\|im_(start|end)\|>|\[/?inst\]|<<sys>>|###\s*(instruction|system))"),
        ("verdict_steering",
         r"\b(mark|classify|set|label|output|respond|answer|return)\b.{0,50}\b(potentially_covered|"
         r"potentially_excluded|as covered|as approved|approved|covered)\b"),
        ("output_suppression",
         r"\b(do not|don't|never)\b.{0,15}\b(cite|mention|reveal|show|flag|escalate|log)\b"),
        ("markup_injection", r"(<\s*script|<\s*iframe|javascript:|<\s*img[^>]+onerror)"),
    ))
_BASE64 = re.compile(r"[A-Za-z0-9+/=]{80,}")


@dataclass(frozen=True)
class Flag:
    kind: str
    detail: str = ""


def strip_hidden(text: str) -> str:
    """Remove zero-width/bidi/soft-hyphen and control characters; NFKC-normalise."""
    return _CONTROL.sub("", _HIDDEN.sub("", unicodedata.normalize("NFKC", text)))


def screen_text(text: str) -> tuple[Flag, ...]:
    flags: list[Flag] = []
    if _HIDDEN.search(text):
        flags.append(Flag("hidden_unicode", "zero-width/bidi/soft-hyphen characters"))
    if _BASE64.search(text):
        flags.append(Flag("encoded_blob", "long base64-like run"))
    folded = fold(strip_hidden(text))
    for name, rx in _PATTERNS:
        if rx.search(folded):
            flags.append(Flag(name))
    return tuple(flags)