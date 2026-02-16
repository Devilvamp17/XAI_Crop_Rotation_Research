from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from services.rag import load_corpus_docs, parse_field_weights, rag_search


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _parse_k_list(raw: str) -> list[int]:
    vals: list[int] = []
    for p in str(raw).split(","):
        p = p.strip()
        if not p:
            continue
        try:
            k = int(p)
            if k > 0:
                vals.append(k)
        except ValueError:
            continue
    if not vals:
        vals = [5, 8, 10]
    return sorted(set(vals))


def _resolve_retrievers(raw: list[str]) -> list[str]:
    out: list[str] = []
    for r in raw:
        v = r.strip().lower()
        if v == "ensemble":
            v = "ensemble_sparse"
        if v in {"baseline_tfidf", "fielded_tfidf", "bm25", "ensemble_sparse"} and v not in out:
            out.append(v)
    if not out:
        out = ["baseline_tfidf", "fielded_tfidf"]
    return out


def _build_eval_queries(
    docs: list[dict[str, Any]],
    sample_n: int,
    seed: int,
) -> list[dict[str, Any]]:
    eligible: list[dict[str, Any]] = []
    for d in docs:
        m = d.get("metadata", {}) or {}
        if _norm(m.get("state")) and _norm(m.get("district")) and _norm(m.get("season")) and _norm(m.get("crop")):
            eligible.append(d)

    if not eligible:
        return []

    rng = np.random.default_rng(seed)
    n = min(int(sample_n), len(eligible))
    picked = rng.choice(len(eligible), size=n, replace=False)

    queries: list[dict[str, Any]] = []
    for i, idx in enumerate(picked):
        d = eligible[int(idx)]
        m = d.get("metadata", {}) or {}
        state = str(m.get("state", "")).strip()
        district = str(m.get("district", "")).strip()
        season = str(m.get("season", "")).strip()
        crop = str(m.get("crop", "")).strip()
        risk = str(m.get("risk", "")).strip()
        suitability = str(m.get("suitability", "")).strip()

        query_fields = {
            "loc": f"STATE {state} DISTRICT {district}",
            "crop_season": f"CROP {crop} SEASON {season}",
            "risk_suit": f"RISK {risk} SUITABILITY {suitability}".strip(),
            "body": f"{district} {state} {crop} {season} crop suitability risk",
        }

        d_state, d_dist, d_season, d_crop = _norm(state), _norm(district), _norm(season), _norm(crop)
        relevant_ids = {
            x["id"]
            for x in docs
            if _norm((x.get("metadata", {}) or {}).get("district")) == d_dist
            and _norm((x.get("metadata", {}) or {}).get("season")) == d_season
            and _norm((x.get("metadata", {}) or {}).get("crop")) == d_crop
        }
        if not relevant_ids:
            relevant_ids = {
                x["id"]
                for x in docs
                if _norm((x.get("metadata", {}) or {}).get("district")) == d_dist
                and _norm((x.get("metadata", {}) or {}).get("season")) == d_season
            }
        if not relevant_ids:
            relevant_ids = {
                x["id"]
                for x in docs
                if _norm((x.get("metadata", {}) or {}).get("state")) == d_state
                and _norm((x.get("metadata", {}) or {}).get("season")) == d_season
            }
        if not relevant_ids:
            relevant_ids = {d["id"]}

        queries.append(
            {
                "query_id": f"q_{i:05d}",
                "query_text": query_fields["body"],
                "query_fields": query_fields,
                "anchor_doc_id": d["id"],
                "relevant_doc_ids": sorted(relevant_ids),
            }
        )
    return queries


def _dcg_binary(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    dcg = 0.0
    for i, doc_id in enumerate(ranked_ids[:k], start=1):
        rel = 1.0 if doc_id in relevant_ids else 0.0
        if rel > 0:
            dcg += rel / np.log2(i + 1)
    return float(dcg)


def _ndcg_binary(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    dcg = _dcg_binary(ranked_ids, relevant_ids, k)
    ideal_len = min(k, len(relevant_ids))
    ideal = [1] * ideal_len
    idcg = sum(float(r) / np.log2(i + 1) for i, r in enumerate(ideal, start=1))
    if idcg <= 0:
        return 0.0
    return float(dcg / idcg)


def _mrr_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    for i, doc_id in enumerate(ranked_ids[:k], start=1):
        if doc_id in relevant_ids:
            return float(1.0 / i)
    return 0.0


def _recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    hit = len(set(ranked_ids[:k]).intersection(relevant_ids))
    return float(hit / len(relevant_ids))


def evaluate(
    *,
    corpus_dir: str,
    retrievers: list[str],
    weights: str,
    alpha: float,
    min_df: int,
    max_df: float,
    ngram: str,
    k_list: list[int],
    sample_n: int,
    seed: int,
    out_dir: Path,
    sample_top_k: int,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    docs = load_corpus_docs(corpus_dir)
    queries = _build_eval_queries(docs, sample_n=sample_n, seed=seed)
    if not queries:
        raise RuntimeError("No eligible queries could be built from corpus.")

    max_k = max(k_list + [sample_top_k])
    metrics: dict[str, Any] = {"retrievers": {}, "k_values": k_list, "query_count": len(queries)}
    csv_rows: list[dict[str, Any]] = []
    query_rankings: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for retriever in retrievers:
        by_k: dict[int, dict[str, float]] = {k: {"recall": 0.0, "mrr": 0.0, "ndcg": 0.0} for k in k_list}
        for q in queries:
            hits = rag_search(
                q["query_text"],
                k=max_k,
                corpus_dir=corpus_dir,
                retriever_type=retriever,
                query_fields=q["query_fields"],
                weights=weights,
                alpha=alpha,
                min_df=min_df,
                max_df=max_df,
                ngram_range=ngram,
            )
            ranked_ids = [str(h.get("id", "")) for h in hits]
            rel = set(q["relevant_doc_ids"])

            per_hit = []
            for h in hits:
                did = str(h.get("id", ""))
                per_hit.append(
                    {
                        "id": did,
                        "score": float(h.get("score", 0.0)),
                        "relevant": did in rel,
                    }
                )
            query_rankings.setdefault(q["query_id"], {})[retriever] = per_hit

            for k in k_list:
                by_k[k]["recall"] += _recall_at_k(ranked_ids, rel, k)
                by_k[k]["mrr"] += _mrr_at_k(ranked_ids, rel, k)
                by_k[k]["ndcg"] += _ndcg_binary(ranked_ids, rel, k)

        qn = float(len(queries))
        metrics["retrievers"][retriever] = {}
        for k in k_list:
            avg = {m: float(v / qn) for m, v in by_k[k].items()}
            metrics["retrievers"][retriever][f"k@{k}"] = avg
            csv_rows.append(
                {
                    "retriever": retriever,
                    "k": k,
                    "recall": avg["recall"],
                    "mrr": avg["mrr"],
                    "ndcg": avg["ndcg"],
                }
            )

    config = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "corpus_dir": corpus_dir,
        "corpus_size": len(docs),
        "query_count": len(queries),
        "retrievers": retrievers,
        "weights": parse_field_weights(weights),
        "weights_raw": weights,
        "alpha": float(alpha),
        "min_df": int(min_df),
        "max_df": float(max_df),
        "ngram": str(ngram),
        "k_values": k_list,
        "sample_top_k": sample_top_k,
        "seed": seed,
    }

    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    with (out_dir / "metrics.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["retriever", "k", "recall", "mrr", "ndcg"])
        w.writeheader()
        w.writerows(csv_rows)
    (out_dir / "run_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    sample_lines = []
    for q in queries[:50]:
        line = {
            "query_id": q["query_id"],
            "query_text": q["query_text"],
            "query_fields": q["query_fields"],
            "relevant_doc_ids_count": len(q["relevant_doc_ids"]),
            "anchor_doc_id": q["anchor_doc_id"],
            "results": {},
        }
        rel = set(q["relevant_doc_ids"])
        for retriever in retrievers:
            hits = query_rankings.get(q["query_id"], {}).get(retriever, [])[:sample_top_k]
            line["results"][retriever] = [
                {
                    "doc_id": h["id"],
                    "score": h["score"],
                    "relevant": h["id"] in rel,
                }
                for h in hits
            ]
        sample_lines.append(line)

    with (out_dir / "queries_sample.jsonl").open("w", encoding="utf-8") as f:
        for line in sample_lines:
            f.write(json.dumps(line, ensure_ascii=True) + "\n")

    # Build markdown summary with simple delta table vs baseline_tfidf.
    baseline = metrics["retrievers"].get("baseline_tfidf", {})
    lines = [
        "# Sparse Retrieval Comparison",
        "",
        f"- Corpus: `{corpus_dir}`",
        f"- Corpus size: `{len(docs)}`",
        f"- Queries evaluated: `{len(queries)}`",
        f"- Retrievers: `{retrievers}`",
        f"- K values: `{k_list}`",
        "",
        "## Metrics",
        "",
        "| Retriever | K | Recall@K | MRR@K | nDCG@K |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in csv_rows:
        lines.append(
            f"| {row['retriever']} | {row['k']} | {row['recall']:.4f} | {row['mrr']:.4f} | {row['ndcg']:.4f} |"
        )

    lines += ["", "## Delta Vs baseline_tfidf", "", "| Retriever | K | ΔRecall | ΔMRR | ΔnDCG |", "| --- | --- | --- | --- | --- |"]
    for row in csv_rows:
        if row["retriever"] == "baseline_tfidf":
            continue
        b = baseline.get(f"k@{row['k']}")
        if not b:
            lines.append(f"| {row['retriever']} | {row['k']} | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |")
            continue
        lines.append(
            f"| {row['retriever']} | {row['k']} | {row['recall'] - b['recall']:+.4f} | {row['mrr'] - b['mrr']:+.4f} | {row['ndcg'] - b['ndcg']:+.4f} |"
        )

    lines += [
        "",
        "## Output Files",
        "",
        "- `metrics.json`",
        "- `metrics.csv`",
        "- `run_config.json`",
        "- `queries_sample.jsonl`",
    ]
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")

    return {
        "metrics": metrics,
        "run_config": config,
        "out_dir": str(out_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate sparse retrievers for RAG corpus.")
    parser.add_argument("--corpus-dir", default="rag_corpus/icar_zones")
    parser.add_argument("--retrievers", nargs="+", default=["baseline_tfidf", "fielded_tfidf", "bm25", "ensemble"])
    parser.add_argument("--weights", default="loc=0.45,crop_season=0.30,risk_suit=0.15,body=0.10")
    parser.add_argument("--alpha", type=float, default=0.6)
    parser.add_argument("--min-df", type=int, default=2)
    parser.add_argument("--max-df", type=float, default=0.9)
    parser.add_argument("--ngram", default="1,2")
    parser.add_argument("--k", type=int, default=8, help="Top-k saved in queries_sample.jsonl entries.")
    parser.add_argument("--k-list", default="5,8,10", help="Comma-separated K values for metrics.")
    parser.add_argument("--sample-n", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="comparison/")
    args = parser.parse_args()

    retrievers = _resolve_retrievers(args.retrievers)
    k_list = _parse_k_list(args.k_list)
    result = evaluate(
        corpus_dir=args.corpus_dir,
        retrievers=retrievers,
        weights=args.weights,
        alpha=args.alpha,
        min_df=args.min_df,
        max_df=args.max_df,
        ngram=args.ngram,
        k_list=k_list,
        sample_n=args.sample_n,
        seed=args.seed,
        out_dir=Path(args.out),
        sample_top_k=max(1, int(args.k)),
    )
    print(json.dumps({"ok": True, "out_dir": result["out_dir"]}, indent=2))


if __name__ == "__main__":
    main()

