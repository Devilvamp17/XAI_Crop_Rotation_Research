# Sparse Retrieval Comparison

- Corpus: `rag_corpus/icar_zones`
- Corpus size: `19425`
- Queries evaluated: `300`
- Retrievers: `['baseline_tfidf', 'fielded_tfidf', 'bm25', 'ensemble_sparse']`
- K values: `[5, 8, 10]`

## Metrics

| Retriever | K | Recall@K | MRR@K | nDCG@K |
| --- | --- | --- | --- | --- |
| baseline_tfidf | 5 | 0.9467 | 0.9467 | 0.9464 |
| baseline_tfidf | 8 | 0.9500 | 0.9472 | 0.9476 |
| baseline_tfidf | 10 | 0.9500 | 0.9472 | 0.9476 |
| fielded_tfidf | 5 | 0.9967 | 1.0000 | 0.9972 |
| fielded_tfidf | 8 | 1.0000 | 1.0000 | 0.9986 |
| fielded_tfidf | 10 | 1.0000 | 1.0000 | 0.9986 |
| bm25 | 5 | 0.9983 | 0.9983 | 0.9975 |
| bm25 | 8 | 1.0000 | 0.9983 | 0.9982 |
| bm25 | 10 | 1.0000 | 0.9983 | 0.9982 |
| ensemble_sparse | 5 | 0.9983 | 1.0000 | 0.9987 |
| ensemble_sparse | 8 | 1.0000 | 1.0000 | 0.9994 |
| ensemble_sparse | 10 | 1.0000 | 1.0000 | 0.9994 |

## Delta Vs baseline_tfidf

| Retriever | K | ΔRecall | ΔMRR | ΔnDCG |
| --- | --- | --- | --- | --- |
| fielded_tfidf | 5 | +0.0500 | +0.0533 | +0.0508 |
| fielded_tfidf | 8 | +0.0500 | +0.0528 | +0.0510 |
| fielded_tfidf | 10 | +0.0500 | +0.0528 | +0.0510 |
| bm25 | 5 | +0.0517 | +0.0517 | +0.0511 |
| bm25 | 8 | +0.0500 | +0.0511 | +0.0506 |
| bm25 | 10 | +0.0500 | +0.0511 | +0.0506 |
| ensemble_sparse | 5 | +0.0517 | +0.0533 | +0.0523 |
| ensemble_sparse | 8 | +0.0500 | +0.0528 | +0.0519 |
| ensemble_sparse | 10 | +0.0500 | +0.0528 | +0.0519 |

## Output Files

- `metrics.json`
- `metrics.csv`
- `run_config.json`
- `queries_sample.jsonl`