from __future__ import annotations

import numpy as np


def _minmax(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    lo = float(np.min(scores))
    hi = float(np.max(scores))
    if hi <= lo:
        return np.zeros_like(scores, dtype=float)
    return (scores - lo) / (hi - lo)


class EnsembleSparseRetriever:
    def __init__(self, tfidf_retriever: object, bm25_retriever: object, alpha: float = 0.6) -> None:
        self.tfidf = tfidf_retriever
        self.bm25 = bm25_retriever
        self.alpha = float(alpha)

    def score(self, query: str, query_fields: dict[str, str] | None = None) -> np.ndarray:
        s_tfidf = np.asarray(self.tfidf.score(query=query, query_fields=query_fields), dtype=float)
        s_bm25 = np.asarray(self.bm25.score(query=query, query_fields=query_fields), dtype=float)
        if s_tfidf.size == 0:
            return s_bm25
        if s_bm25.size == 0:
            return s_tfidf
        s_tfidf_n = _minmax(s_tfidf)
        s_bm25_n = _minmax(s_bm25)
        return self.alpha * s_bm25_n + (1.0 - self.alpha) * s_tfidf_n

