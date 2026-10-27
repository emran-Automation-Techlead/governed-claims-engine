# Retrieval variants (generated)

Embedding: e8f8c211226b894fcb81acc59f3b34ba3efd5f42. Baseline reproduction (M2 analyzer vs frozen M2 numbers): {'bm25': True, 'hybrid_rrf': True, 'vector': True}

## M2 cases (49 answerable + 3 unanswerable), original 4-document corpus

| variant | method | hit@5 | Recall@3 | Recall@1 | MRR | spurious/unans. | failures |
|---|---|---|---|---|---|---|---|
| M2 analyzer (baseline) | bm25 | 0.857 | 0.816 | 0.745 | 0.823 | 1/3 | Q18, Q22, Q24, Q45, Q47, Q48, Q49 |
| M2 analyzer (baseline) | hybrid_rrf | 0.959 | 0.898 | 0.806 | 0.913 | 3/3 | Q18, Q47 |
| M2 analyzer (baseline) | vector | 0.878 | 0.806 | 0.622 | 0.783 | 3/3 | Q01, Q02, Q03, Q05, Q20, Q47 |
| + stopwords | bm25 | 0.776 | 0.755 | 0.694 | 0.755 | 0/3 | Q18, Q19, Q20, Q21, Q22, Q24, Q26, Q45, Q47, Q48, Q49 |
| + stopwords | hybrid_rrf | 0.959 | 0.949 | 0.806 | 0.924 | 3/3 | Q20, Q47 |
| + stopwords | vector | 0.878 | 0.806 | 0.622 | 0.783 | 3/3 | Q01, Q02, Q03, Q05, Q20, Q47 |
| + stopwords + subwords | bm25 | 0.776 | 0.755 | 0.673 | 0.745 | 0/3 | Q18, Q19, Q20, Q21, Q22, Q24, Q26, Q45, Q47, Q48, Q49 |
| + stopwords + subwords | hybrid_rrf | 0.959 | 0.949 | 0.786 | 0.914 | 3/3 | Q20, Q47 |
| + stopwords + subwords | vector | 0.878 | 0.806 | 0.622 | 0.783 | 3/3 | Q01, Q02, Q03, Q05, Q20, Q47 |
| + subwords only | bm25 | 0.837 | 0.816 | 0.704 | 0.802 | 1/3 | Q18, Q20, Q22, Q24, Q45, Q47, Q48, Q49 |
| + subwords only | hybrid_rrf | 0.959 | 0.898 | 0.765 | 0.892 | 3/3 | Q18, Q47 |
| + subwords only | vector | 0.878 | 0.806 | 0.622 | 0.783 | 3/3 | Q01, Q02, Q03, Q05, Q20, Q47 |

## Held-out cases (7-document corpus, per-case document scope)

| variant | method | hit@5 all | Recall@3 all | spurious/unans. | hit@5 compound (n=7) | hit@5 non-compound | failed ids |
|---|---|---|---|---|---|---|---|
| M2 analyzer (baseline) | bm25 | 0.783 | 0.728 | 5/9 | 0.714 | 0.795 | HO23, HO25, HO28, HO29, HO30, HO31, HO32, HO33, HO34, HO36 |
| M2 analyzer (baseline) | hybrid_rrf | 1.000 | 0.967 | 9/9 | 1.000 | 1.000 |  |
| M2 analyzer (baseline) | vector | 1.000 | 0.957 | 9/9 | 1.000 | 1.000 |  |
| + stopwords | bm25 | 0.783 | 0.772 | 2/9 | 0.714 | 0.795 | HO23, HO25, HO28, HO29, HO30, HO31, HO32, HO33, HO34, HO36 |
| + stopwords | hybrid_rrf | 1.000 | 0.989 | 9/9 | 1.000 | 1.000 |  |
| + stopwords | vector | 1.000 | 0.957 | 9/9 | 1.000 | 1.000 |  |
| + stopwords + subwords | bm25 | 0.804 | 0.793 | 2/9 | 0.857 | 0.795 | HO23, HO28, HO29, HO30, HO31, HO32, HO33, HO34, HO36 |
| + stopwords + subwords | hybrid_rrf | 1.000 | 0.989 | 9/9 | 1.000 | 1.000 |  |
| + stopwords + subwords | vector | 1.000 | 0.957 | 9/9 | 1.000 | 1.000 |  |
| + subwords only | bm25 | 0.804 | 0.772 | 5/9 | 0.857 | 0.795 | HO23, HO28, HO29, HO30, HO31, HO32, HO33, HO34, HO36 |
| + subwords only | hybrid_rrf | 1.000 | 0.967 | 9/9 | 1.000 | 1.000 |  |
| + subwords only | vector | 1.000 | 0.957 | 9/9 | 1.000 | 1.000 |  |

## RRF sensitivity (hybrid, M2 analyzer) - measurement only, defaults unchanged

| setting | M2 hit@5 | M2 Recall@3 | held-out hit@5 | held-out Recall@3 |
|---|---|---|---|---|
| k=10,depth=5 | 0.959 | 0.929 | 1.000 | 0.967 |
| k=10,depth=20 | 0.959 | 0.918 | 1.000 | 0.967 |
| k=60,depth=5 | 0.959 | 0.929 | 1.000 | 0.967 |
| k=60,depth=20 | 0.959 | 0.898 | 1.000 | 0.967 |
| k=200,depth=5 | 0.959 | 0.929 | 1.000 | 0.967 |
| k=200,depth=20 | 0.959 | 0.898 | 1.000 | 0.967 |
