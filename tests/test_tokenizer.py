import pytest

from claims_engine.bm25 import BM25Index, analyze, fold, tokenize, tokenize_legacy


@pytest.mark.parametrize("raw,expected", [
    ("Dégât des eaux", "degat des eaux"),
    ("ÉCOLE Été", "ecole ete"),
    ("Verschleiß", "verschleiss"),
    ("Schäden Ausschlüsse Größe", "schaden ausschlusse grosse"),
    ("cœur Œuvre", "coeur oeuvre"),
    ("FRANÇAIS à la carte", "francais a la carte"),
])
def test_fold_removes_accents_and_casefolds(raw, expected):
    assert fold(raw) == expected


def test_accented_and_unaccented_forms_produce_same_tokens():
    assert tokenize("Dégât des eaux") == tokenize("DEGAT DES EAUX")
    assert tokenize("Verschleiß") == tokenize("verschleiss") == ["verschleiss"]


def test_french_elision_letters_dropped_by_analyzer_but_tokenize_unchanged():
    assert analyze("l'humidité d'eau") == ["humidite", "eau"]
    assert analyze("l\u2019incendie") == ["incendie"]  # typographic apostrophe
    assert tokenize("a b") == ["a", "b"]  # Milestone-1 contract


def test_german_compound_stays_one_token():
    assert tokenize("Leitungswasserschaden") == ["leitungswasserschaden"]


@pytest.mark.parametrize("text,tokens", [
    ("clause 4.3", ["clause", "4.3"]),
    ("see 4.2.1 and 12.10", ["see", "4.2.1", "and", "12.10"]),
    ("Ziffer 3.2.", ["ziffer", "3.2"]),  # trailing full stop is not part of the id
    ("EUR 1,500", ["eur", "1", "500"]),
    ("60 jours", ["60", "jours"]),
])
def test_clause_identifiers_and_numbers_preserved(text, tokens):
    assert tokenize(text) == tokens


def test_hyphenated_words_keep_whole_and_analyze_adds_parts():
    assert tokenize("pre-existing") == ["pre-existing"]
    assert analyze("pre-existing") == ["pre-existing", "pre", "existing"]
    assert analyze("clause 3.1") == ["clause", "3.1"]  # numeric ids are not split


def test_legacy_tokenizer_breaks_on_accents_new_one_does_not():
    assert tokenize_legacy("Dégât") == ["d", "g", "t"]
    assert tokenize("Dégât") == ["degat"]


def test_non_latin_scripts_are_not_discarded():
    assert tokenize("保险 ασφάλεια") == ["保险", "ασφαλεια"]


def test_bm25_matches_accent_insensitively_french():
    docs = ["Dégât des eaux : rupture soudaine de canalisation", "Vol avec effraction constatée"]
    idx = BM25Index(docs)
    assert idx.search("degat des eaux")[0].index == 0
    assert idx.search("DÉGÂT")[0].index == 0


def test_bm25_matches_eszett_variants_german():
    idx = BM25Index(["Verschleiß und Abnutzung", "Leerstand von 60 Tagen"])
    assert idx.search("Verschleiss")[0].index == 0
    assert idx.search("verschleiß")[0].index == 0


def test_exact_clause_id_query_ranks_that_clause_first():
    docs = ["3.1 Burst pipes are covered", "3.2 Gradual leakage is excluded", "4.3 Unoccupied"]
    idx = BM25Index(docs)
    assert idx.search("3.2")[0].index == 1
    assert idx.search("4.3")[0].index == 2
    assert idx.search("3") == []  # "3" alone must not match "3.1" / "3.2" tokens


def test_analyzer_hook_used_for_query_and_documents():
    idx = BM25Index(["pre-existing illness", "other"], analyzer=analyze)
    assert idx.search("existing")[0].index == 0