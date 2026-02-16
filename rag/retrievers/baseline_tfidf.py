from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from rag.retrievers.base import TfidfConfig


class BaselineTfidfRetriever:
    def __init__(self, docs: list[dict[str, Any]], config: TfidfConfig, stop_words: str | None = "english") -> None:
        self.docs = docs
        self.vectorizer = TfidfVectorizer(
            ngram_range=config.ngram_range,
            sublinear_tf=config.sublinear_tf,
            smooth_idf=config.smooth_idf,
            min_df=config.min_df,
            max_df=config.max_df,
            token_pattern=config.token_pattern,
            stop_words=stop_words,
            lowercase=True,
        )
        texts = [str(d.get("text", "")) for d in docs]
        if texts:
            try:
                self.doc_matrix = self.vectorizer.fit_transform(texts)
                self.doc_matrix_norm = normalize(self.doc_matrix, norm="l2")
            except ValueError:
                self.doc_matrix = None
                self.doc_matrix_norm = None
        else:
            self.doc_matrix = None
            self.doc_matrix_norm = None

    def score(self, query: str, query_fields: dict[str, str] | None = None) -> np.ndarray:
        if not self.docs or self.doc_matrix_norm is None:
            return np.zeros(0, dtype=float)
        q_text = (query_fields or {}).get("body") or query
        q_text = str(q_text).strip()
        if not q_text:
            return np.zeros(len(self.docs), dtype=float)
        qvec = self.vectorizer.transform([q_text])
        qvec_norm = normalize(qvec, norm="l2")
        sims = (self.doc_matrix_norm @ qvec_norm.T).toarray().ravel()
        return sims.astype(float)
