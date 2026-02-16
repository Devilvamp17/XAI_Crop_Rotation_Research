.PHONY: eval-sparse-retrieval

eval-sparse-retrieval:
	PYTHONPATH=. uv run python scripts/eval_sparse_retrieval.py \
		--k 8 \
		--k-list 5,8,10 \
		--out comparison/ \
		--retrievers baseline_tfidf fielded_tfidf bm25 ensemble \
		--weights loc=0.45,crop_season=0.30,risk_suit=0.15,body=0.10 \
		--alpha 0.6 \
		--min-df 2 \
		--max-df 0.9 \
		--ngram 1,2
