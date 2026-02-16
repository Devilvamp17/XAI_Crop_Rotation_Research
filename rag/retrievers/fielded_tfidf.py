from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from rag.retrievers.base import TfidfConfig


FIELD_NAMES = ("loc", "crop_season", "risk_suit", "body")
DEFAULT_FIELD_WEIGHTS: dict[str, float] = {
    "loc": 0.45,
    "crop_season": 0.30,
    "risk_suit": 0.15,
    "body": 0.10,
}


class FieldedTfidfRetriever:
    def __init__(
        self,
        docs: list[dict[str, Any]],
        config: TfidfConfig,
        field_weights: dict[str, float] | None = None,
        stop_words: str | None = "english",
    ) -> None:
        self.docs = docs
        self.weights = {**DEFAULT_FIELD_WEIGHTS, **(field_weights or {})}
        self.vectorizers: dict[str, TfidfVectorizer] = {}
        self.doc_mats_norm: dict[str, Any] = {}

        for field in FIELD_NAMES:
            vec = TfidfVectorizer(
                ngram_range=config.ngram_range,
                sublinear_tf=config.sublinear_tf,
                smooth_idf=config.smooth_idf,
                min_df=config.min_df,
                max_df=config.max_df,
                token_pattern=config.token_pattern,
                stop_words=stop_words,
                lowercase=True,
            )
            texts = [str((d.get("fields", {}) or {}).get(field, "")) for d in docs]
            if texts:
                try:
                    mat = vec.fit_transform(texts)
                except ValueError:
                    continue
                self.vectorizers[field] = vec
                self.doc_mats_norm[field] = normalize(mat, norm="l2")

    def score(self, query: str, query_fields: dict[str, str] | None = None) -> np.ndarray:
        if not self.docs:
            return np.zeros(0, dtype=float)

        qf = query_fields or {}
        total = np.zeros(len(self.docs), dtype=float)
        active_weight = 0.0

        for field, vec in self.vectorizers.items():
            qtext = str(qf.get(field, "")).strip()
            if not qtext:
                if field == "body":
                    qtext = str(query).strip()
            if not qtext:
                continue
            qvec = vec.transform([qtext])
            qvec_norm = normalize(qvec, norm="l2")
            sims = (self.doc_mats_norm[field] @ qvec_norm.T).toarray().ravel().astype(float)
            weight = float(self.weights.get(field, 0.0))
            if weight <= 0:
                continue
            total += weight * sims
            active_weight += weight

        if active_weight > 0:
            total = total / active_weight
        return total
