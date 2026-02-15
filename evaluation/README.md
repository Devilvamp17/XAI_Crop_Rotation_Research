# Evaluation Module

Run full evaluation:

```bash
python -m evaluation.run_all
```

Outputs are written to:

`evaluation/out/<run_id>/`

Structure:
- `tables/*.csv`, `tables/*.md`
- `plots/*.png`
- `summary/ablation_summary.json`
- `summary/report.md`

The pipeline is offline-first and uses local repository artifacts when available.
