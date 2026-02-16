from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

import numpy as np

from rag.retrievers.base import DEFAULT_TOKEN_PATTERN


class BM25Retriever:
    def __init__(
        self,
        docs: list[dict[str, Any]],
        k1: float = 1.5,
        b: float = 0.75,
        token_pattern: str = DEFAULT_TOKEN_PATTERN,
    ) -> None:
        self.docs = docs
        self.k1 = float(k1)
        self.b = float(b)
        self._tok_re = re.compile(token_pattern)

        self.doc_len: list[int] = []
        self.avgdl: float = 0.0
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.idf: dict[str, float] = {}

        self._fit()

    def _tokenize(self, text: str) -> list[str]:
        return [t.lower() for t in self._tok_re.findall(text or "")]

    def _fit(self) -> None:
        if not self.docs:
            return
        df_counter: dict[str, int] = defaultdict(int)
        for i, doc in enumerate(self.docs):
            text = str(doc.get("text", ""))
            toks = self._tokenize(text)
            tf = Counter(toks)
            self.doc_len.append(sum(tf.values()))
            for term, freq in tf.items():
                self.postings[term].append((i, int(freq)))
                df_counter[term] += 1
        self.avgdl = float(np.mean(self.doc_len)) if self.doc_len else 0.0
        n_docs = len(self.docs)
        for term, df in df_counter.items():
            # BM25 IDF with +1 for stability
            self.idf[term] = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))

    def score(self, query: str, query_fields: dict[str, str] | None = None) -> np.ndarray:
        if not self.docs:
            return np.zeros(0, dtype=float)
        q_parts: list[str] = []
        if query_fields:
            q_parts.extend(str(v) for v in query_fields.values() if str(v).strip())
        if query:
            q_parts.append(str(query))
        q_tokens = self._tokenize(" ".join(q_parts))
        if not q_tokens:
            return np.zeros(len(self.docs), dtype=float)

        q_tf = Counter(q_tokens)
        scores = np.zeros(len(self.docs), dtype=float)
        avgdl = self.avgdl if self.avgdl > 0 else 1.0

        for term, q_freq in q_tf.items():
            postings = self.postings.get(term, [])
            if not postings:
                continue
            idf = self.idf.get(term, 0.0)
            for doc_idx, tf in postings:
                dl = self.doc_len[doc_idx] if doc_idx < len(self.doc_len) else 0
                denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / avgdl))
                if denom <= 0:
                    continue
                scores[doc_idx] += idf * ((tf * (self.k1 + 1.0)) / denom) * q_freq
        return scores

