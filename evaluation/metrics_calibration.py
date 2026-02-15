from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from evaluation.config import DATASET_PATH, DEFAULT_TEST_SPLIT, XAI_EVAL_DIR
from evaluation.io_utils import safe_load_json, write_csv, write_md_table
from evaluation.metrics_model import load_dataset_xlsx


def _try_get_xgb() -> Any | None:
    try:
        from xgboost import XGBClassifier

        return XGBClassifier(
            random_state=42,
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            eval_metric="mlogloss",
        )
    except Exception:
        return None


def _calibration_from_probs(proba: np.ndarray, y_true: np.ndarray, bins: int = 10) -> dict[str, Any]:
    pred = np.argmax(proba, axis=1)
    conf = np.max(proba, axis=1)
    correct = (pred == y_true).astype(float)
    edges = np.linspace(0.0, 1.0, bins + 1)

    acc: list[float] = []
    avg: list[float] = []
    sizes: list[int] = []
    ece = 0.0

    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (conf >= lo) & (conf < hi if i < bins - 1 else conf <= hi)
        n = int(np.sum(mask))
        sizes.append(n)
        if n == 0:
            acc.append(0.0)
            avg.append(0.0)
            continue
        a = float(np.mean(correct[mask]))
        c = float(np.mean(conf[mask]))
        acc.append(a)
        avg.append(c)
        ece += abs(a - c) * (n / len(conf))

    return {
        "bins": edges.tolist(),
        "accuracy": acc,
        "avg_confidence": avg,
        "bucket_sizes": sizes,
        "ece": float(ece),
    }


def _plot_curve(model: str, cal: dict[str, Any], out: Path) -> None:
    x = np.array(cal.get("avg_confidence", []), dtype=float)
    y = np.array(cal.get("accuracy", []), dtype=float)
    plt.figure(figsize=(6, 5))
    sns.lineplot(x=x, y=y, marker="o", label=model)
    sns.lineplot(x=[0, 1], y=[0, 1], linestyle="--", color="black", label="ideal")
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.xlabel("Average Confidence")
    plt.ylabel("Empirical Accuracy")
    plt.title(f"Calibration Curve: {model}")
    plt.tight_layout()
    plt.savefig(out, dpi=200)
    plt.close()


def run(run_dir: Path) -> dict[str, Any]:
    notes: list[str] = []
    tables_dir = run_dir / "tables"
    plots_dir = run_dir / "plots"

    calib_file = safe_load_json(XAI_EVAL_DIR / "calibration_report.json")

    model_rows: list[dict[str, Any]] = []
    per_model: dict[str, dict[str, Any]] = {}

    if calib_file and isinstance(calib_file.get("per_model"), dict):
        per_model = calib_file["per_model"]
    else:
        if calib_file:
            per_model["xgboost"] = calib_file

        try:
            X, y, _ = load_dataset_xlsx(DATASET_PATH)
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=DEFAULT_TEST_SPLIT,
                random_state=42,
                stratify=y,
            )
            models = {
                "logistic_regression": LogisticRegression(max_iter=3000, random_state=42),
                "random_forest": RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1),
            }
            xgb = _try_get_xgb()
            if xgb is not None:
                models["xgboost"] = xgb

            for name, model in models.items():
                model.fit(X_train, y_train)
                proba = model.predict_proba(X_test)
                per_model.setdefault(name, _calibration_from_probs(proba, y_test))
        except Exception as exc:
            notes.append(f"Calibration recompute failed: {exc}")

    for model, cal in per_model.items():
        model_rows.append({"model": model, "ece": float(cal.get("ece", np.nan))})
        try:
            _plot_curve(model, cal, plots_dir / f"calibration_curve_{model}.png")
        except Exception as exc:
            notes.append(f"Failed plotting calibration for {model}: {exc}")

    df = pd.DataFrame(model_rows)
    write_csv(df, tables_dir / "calibration_metrics.csv")
    write_md_table(df, tables_dir / "calibration_metrics.md", "Calibration Metrics")

    return {"notes": notes, "available": not df.empty, "per_model": per_model}
