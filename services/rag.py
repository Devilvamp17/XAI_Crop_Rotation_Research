from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass
class _RAGIndex:
    docs: list[dict[str, str]]
    matrix: np.ndarray
    vectorizer: TfidfVectorizer


def _parse_markdown(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8").strip()
    lines = text.splitlines()
    if lines and lines[0].startswith("#"):
        title = lines[0].lstrip("#").strip()
        body = "\n".join(lines[1:]).strip()
    else:
        title = path.stem.replace("_", " ").title()
        body = text
    return title, body


@lru_cache(maxsize=8)
def build_index(corpus_dir: str = "rag_corpus/") -> _RAGIndex:
    root = Path(corpus_dir)
    files = sorted(root.rglob("*.md"))
    docs: list[dict[str, str]] = []
    for idx, path in enumerate(files, start=1):
        title, body = _parse_markdown(path)
        docs.append(
            {
                "id": f"chunk_{idx:06d}",
                "title": title,
                "text": body,
                "source": str(path),
            }
        )

    if not docs:
        vectorizer = TfidfVectorizer(stop_words="english")
        return _RAGIndex(docs=[], matrix=np.zeros((0, 0), dtype=float), vectorizer=vectorizer)

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([d["text"] for d in docs]).toarray()
    return _RAGIndex(docs=docs, matrix=matrix, vectorizer=vectorizer)


def rag_search(query: str, k: int = 5, corpus_dir: str = "rag_corpus/") -> list[dict[str, str]]:
    idx = build_index(corpus_dir)
    if not idx.docs:
        return []

    qvec = idx.vectorizer.transform([query]).toarray()[0]
    if float(np.linalg.norm(qvec)) == 0.0:
        return idx.docs[:k]

    doc_norms = np.linalg.norm(idx.matrix, axis=1) + 1e-12
    q_norm = float(np.linalg.norm(qvec)) + 1e-12
    sims = (idx.matrix @ qvec) / (doc_norms * q_norm)

    top_ids = np.argsort(sims)[::-1][: max(1, k)]
    out: list[dict[str, str]] = []
    for i in top_ids:
        d = idx.docs[int(i)]
        out.append(
            {
                "id": d["id"],
                "title": d["title"],
                "text": d["text"],
                "source": d["source"],
            }
        )
    return out
