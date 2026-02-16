from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Any

import numpy as np

from core import settings
from rag.retrievers import (
    BM25Retriever,
    BaselineTfidfRetriever,
    EnsembleSparseRetriever,
    FieldedTfidfRetriever,
)
from rag.retrievers.base import DEFAULT_TOKEN_PATTERN, TfidfConfig

FIELD_NAMES = ("loc", "crop_season", "risk_suit", "body")
DEFAULT_FIELD_WEIGHTS: dict[str, float] = {
    "loc": 0.45,
    "crop_season": 0.30,
    "risk_suit": 0.15,
    "body": 0.10,
}

_TAG_LINE_RE = re.compile(r"(?m)^([A-Z_]+)\s*:\s*(.*)$")
_SEASON_SYNONYMS = {
    "monsoon": "kharif",
    "winter": "rabi",
    "summer": "zaid",
}
_QUERY_TAG_RE = re.compile(
    r"\b(STATE|DISTRICT|CROP|SEASON|RISK|SUITABILITY|ZONE|ZONE_ID|FAMILY)\s+",
    flags=re.IGNORECASE,
)


@dataclass
class _RAGIndex:
    docs: list[dict[str, Any]]
    retriever: Any
    retriever_type: str
    config: dict[str, Any]


def _normalize_text(text: str) -> str:
    out = text
    for src, dst in _SEASON_SYNONYMS.items():
        out = re.sub(rf"\b{re.escape(src)}\b", dst, out, flags=re.IGNORECASE)
    return out


def _canonicalize_query_tags(text: str) -> str:
    # Normalize "STATE Punjab" -> "STATE:Punjab" to align with tagged corpus tokens.
    return _QUERY_TAG_RE.sub(lambda m: f"{m.group(1).upper()}:", text or "")


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


def _extract_tag_map(text: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for k, v in _TAG_LINE_RE.findall(text or ""):
        tags[k.lower()] = v.strip()
    return tags


def _strip_tag_lines(text: str) -> str:
    return _TAG_LINE_RE.sub("", text or "").strip()


def _doc_fields(meta: dict[str, str], body: str) -> dict[str, str]:
    state = meta.get("state", "")
    district = meta.get("district", "")
    crop = meta.get("crop", "")
    season = meta.get("season", "")
    risk = meta.get("risk", "")
    suitability = meta.get("suitability", "")
    remainder = _strip_tag_lines(body)

    loc = " ".join([f"STATE:{state}".strip(), f"DISTRICT:{district}".strip()]).strip()
    crop_season = " ".join([f"CROP:{crop}".strip(), f"SEASON:{season}".strip()]).strip()
    risk_suit = " ".join([f"RISK:{risk}".strip(), f"SUITABILITY:{suitability}".strip()]).strip()
    body_field = remainder if remainder else body

    return {
        "loc": _normalize_text(loc),
        "crop_season": _normalize_text(crop_season),
        "risk_suit": _normalize_text(risk_suit),
        "body": _normalize_text(body_field),
    }


def parse_field_weights(weights: str | dict[str, float] | None) -> dict[str, float]:
    if isinstance(weights, dict):
        out = {**DEFAULT_FIELD_WEIGHTS}
        for k, v in weights.items():
            if k in FIELD_NAMES:
                out[k] = float(v)
        return out

    out = {**DEFAULT_FIELD_WEIGHTS}
    raw = (weights or "").strip()
    if not raw:
        return out
    for part in raw.split(","):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        if k not in FIELD_NAMES:
            continue
        try:
            out[k] = float(v.strip())
        except ValueError:
            continue
    return out


def parse_ngram(raw: str | tuple[int, int] | None) -> tuple[int, int]:
    if isinstance(raw, tuple) and len(raw) == 2:
        return int(raw[0]), int(raw[1])
    text = str(raw or "1,2").strip()
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) != 2:
        return (1, 2)
    try:
        lo = int(parts[0])
        hi = int(parts[1])
        if lo <= 0 or hi < lo:
            return (1, 2)
        return (lo, hi)
    except ValueError:
        return (1, 2)


def load_corpus_docs(corpus_dir: str = "rag_corpus/") -> list[dict[str, Any]]:
    root = Path(corpus_dir)
    files = sorted(root.rglob("*.md"))
    docs: list[dict[str, Any]] = []
    for idx, path in enumerate(files, start=1):
        title, body = _parse_markdown(path)
        tags = _extract_tag_map(body)
        fields = _doc_fields(tags, body)
        docs.append(
            {
                "id": f"chunk_{idx:06d}",
                "title": title,
                "text": body,
                "source": str(path),
                "metadata": {
                    "state": tags.get("state", ""),
                    "district": tags.get("district", ""),
                    "season": tags.get("season", ""),
                    "crop": tags.get("crop", ""),
                    "risk": tags.get("risk", ""),
                    "suitability": tags.get("suitability", ""),
                },
                "fields": fields,
            }
        )
    return docs


def list_available_retrievers() -> list[str]:
    return ["baseline_tfidf", "fielded_tfidf", "bm25", "ensemble_sparse"]


def build_query_fields(query: str, query_fields: dict[str, str] | None = None) -> dict[str, str]:
    base = {"loc": "", "crop_season": "", "risk_suit": "", "body": _normalize_text(query or "")}
    if not query_fields:
        return base
    for k in FIELD_NAMES:
        if k in query_fields and str(query_fields[k]).strip():
            raw = _normalize_text(str(query_fields[k]))
            if k in {"loc", "crop_season", "risk_suit"}:
                raw = _canonicalize_query_tags(raw)
            base[k] = raw
    return base


def _weights_key(weights: dict[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(sorted((k, float(v)) for k, v in weights.items() if k in FIELD_NAMES))


def _resolve_retriever_type(raw: str | None) -> str:
    val = (raw or settings.rag_retriever or "baseline_tfidf").strip().lower()
    if val == "ensemble":
        return "ensemble_sparse"
    if val not in {"baseline_tfidf", "fielded_tfidf", "bm25", "ensemble_sparse"}:
        return "baseline_tfidf"
    return val


def _safe_tfidf_thresholds(n_docs: int, min_df: int | float, max_df: int | float) -> tuple[int | float, int | float]:
    if n_docs <= 3:
        return 1, 1.0
    if isinstance(min_df, int):
        min_df = max(1, min(min_df, n_docs - 1))
    if isinstance(max_df, float):
        max_df = max(0.5, min(max_df, 1.0))
    return min_df, max_df


@lru_cache(maxsize=32)
def _build_index_cached(
    corpus_dir: str,
    retriever_type: str,
    weights_key: tuple[tuple[str, float], ...],
    alpha: float,
    min_df: int,
    max_df: float,
    ngram: tuple[int, int],
) -> _RAGIndex:
    docs = load_corpus_docs(corpus_dir)
    weights = dict(weights_key)
    tf_min_df, tf_max_df = _safe_tfidf_thresholds(len(docs), min_df=min_df, max_df=max_df)
    tf_cfg = TfidfConfig(
        ngram_range=ngram,
        sublinear_tf=True,
        smooth_idf=True,
        min_df=tf_min_df,
        max_df=tf_max_df,
        token_pattern=DEFAULT_TOKEN_PATTERN,
    )

    if retriever_type == "fielded_tfidf":
        retriever = FieldedTfidfRetriever(docs=docs, config=tf_cfg, field_weights=weights, stop_words="english")
    elif retriever_type == "bm25":
        retriever = BM25Retriever(docs=docs, token_pattern=DEFAULT_TOKEN_PATTERN)
    elif retriever_type == "ensemble_sparse":
        tf = FieldedTfidfRetriever(docs=docs, config=tf_cfg, field_weights=weights, stop_words="english")
        bm = BM25Retriever(docs=docs, token_pattern=DEFAULT_TOKEN_PATTERN)
        retriever = EnsembleSparseRetriever(tfidf_retriever=tf, bm25_retriever=bm, alpha=alpha)
    else:
        retriever = BaselineTfidfRetriever(docs=docs, config=tf_cfg, stop_words="english")

    return _RAGIndex(
        docs=docs,
        retriever=retriever,
        retriever_type=retriever_type,
        config={
            "weights": weights,
            "alpha": alpha,
            "min_df": tf_min_df,
            "max_df": tf_max_df,
            "ngram_range": ngram,
        },
    )


def build_index(
    corpus_dir: str = "rag_corpus/",
    retriever_type: str | None = None,
    weights: str | dict[str, float] | None = None,
    alpha: float | None = None,
    min_df: int | None = None,
    max_df: float | None = None,
    ngram_range: tuple[int, int] | str | None = None,
) -> _RAGIndex:
    rt = _resolve_retriever_type(retriever_type)
    ws = parse_field_weights(weights if weights is not None else settings.rag_field_weights)
    a = float(alpha if alpha is not None else settings.rag_ensemble_alpha)
    mdf = int(min_df if min_df is not None else settings.rag_min_df)
    xdf = float(max_df if max_df is not None else settings.rag_max_df)
    ngr = parse_ngram(ngram_range if ngram_range is not None else settings.rag_ngram)
    return _build_index_cached(corpus_dir, rt, _weights_key(ws), a, mdf, xdf, ngr)


def rag_search(
    query: str,
    k: int = 5,
    corpus_dir: str = "rag_corpus/",
    retriever_type: str | None = None,
    query_fields: dict[str, str] | None = None,
    weights: str | dict[str, float] | None = None,
    alpha: float | None = None,
    min_df: int | None = None,
    max_df: float | None = None,
    ngram_range: tuple[int, int] | str | None = None,
) -> list[dict[str, Any]]:
    idx = build_index(
        corpus_dir=corpus_dir,
        retriever_type=retriever_type,
        weights=weights,
        alpha=alpha,
        min_df=min_df,
        max_df=max_df,
        ngram_range=ngram_range,
    )
    if not idx.docs:
        return []

    q_fields = build_query_fields(query, query_fields=query_fields)
    scores = np.asarray(idx.retriever.score(query=q_fields.get("body", query), query_fields=q_fields), dtype=float)
    if scores.size == 0:
        return []

    if np.allclose(scores, 0.0):
        top_ids = np.arange(min(max(1, int(k)), len(idx.docs)))
    else:
        top_ids = np.argsort(scores)[::-1][: max(1, int(k))]

    out: list[dict[str, Any]] = []
    for i in top_ids:
        d = idx.docs[int(i)]
        out.append(
            {
                "id": d["id"],
                "title": d["title"],
                "text": d["text"],
                "source": d["source"],
                "score": float(scores[int(i)]),
                "metadata": d.get("metadata", {}),
            }
        )
    return out
