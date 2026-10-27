"""Closed-class function-word lists for EN / FR / DE (articles, prepositions, pronouns, auxiliaries).

Design rules (enforced by tests):
* Only grammatical function words. NO domain vocabulary, and nothing chosen by looking at the
  evaluation queries - the lists follow the usual closed-class categories.
* Words that carry insurance meaning are PROTECTED and never removed: negations (not, kein, pas),
  conditions/exceptions (if, unless, except, sauf, wenn, es sei denn) and restrictions (only,
  uniquement, nur, without, sans, ohne). Dropping "not" from "we do not cover" would flip a clause.
* Matching is done on accent-folded forms, so the lists are folded at import.
"""
from __future__ import annotations

from .bm25 import fold

_EN = """a an the and or but of in on at to for from by with about as into over under between through
during before after above below up down out off again further then once here there when where why
how all any both each few more most other some such own same so than too very can will just should
now is are was were be been being have has had do does did having would could might must i me my we
our you your he him his she her it its they them their what which who whom this that these those am
also"""
_FR = """le la les l un une des du de d et ou mais donc or car dans en sur sous avec par pour au aux a
ce cet cette ces mon ma mes ton ta tes son sa ses notre nos votre vos leur leurs je tu il elle on
nous vous ils elles me te se lui y qui que quoi dont ou est sont etait etaient ete etre ai as avons
avez ont avait avoir fait faire tres tout tous toute toutes comme aussi cela ceci ca c j m n s t qu""" 
_DE = """der die das den dem des ein eine einen einem einer eines und oder aber doch denn sondern in im
an am auf aus bei mit nach von vom zu zum zur uber unter vor fur durch gegen um bis seit ab als wie
ich du er sie es wir ihr mein dein sein unser euer sich mir mich dir dich ihm ihn uns euch ihnen ist
sind war waren wird werden wurde wurden hat haben hatte hatten kann konnen muss mussen soll sollen
will wollen auch noch so da dann dass hier dort wo was wer wem wen welche welcher welches diese
dieser dieses jede jeder jedes alle allen aller sehr mehr""" 

# Negation / condition / restriction words: must survive stopword removal.
PROTECTED = frozenset(fold(w) for w in ["not", "no", "nor", "never", "none", "without", "unless", "except", "only", "if", "until", "ne", "pas", "non", "jamais", "sans", "sauf", "si", "seulement", "uniquement", "aucun", "aucune", "nicht", "kein", "keine", "keinen", "keiner", "ohne", "nie", "niemals", "wenn", "nur", "ausser", "sofern", "es", "sei", "denn"])


def _build(raw: object) -> frozenset[str]:
    words = raw if isinstance(raw, list) else str(raw).split()
    return frozenset(fold(w) for w in words) - PROTECTED


STOPWORDS: frozenset[str] = _build(_EN) | _build(_FR) | _build(_DE)