from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from evaluation.config import DATASET_PATH, DEFAULT_TEST_SPLIT
from evaluation.io_utils import write_csv, write_md_table


@dataclass
class ModelArtifacts:
    name: str
    estimator: Any


def load_dataset_xlsx(path: str | Path = DATASET_PATH) -> tuple[pd.DataFrame, np.ndarray, LabelEncoder]:
    df = pd.read_excel(path)
    feature_cols = ["N", "P", "K", "temperature", "humidity", "ph"]
    X = df[feature_cols].copy()
    le = LabelEncoder()
    y = le.fit_transform(df["label"].astype(str))
    return X, y, le


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


def _top3_accuracy(model: Any, X_test: pd.DataFrame, y_test: np.ndarray) -> float:
    proba = model.predict_proba(X_test)
    top3 = np.argsort(proba, axis=1)[:, -3:]
    return float(np.mean([y_test[i] in top3[i] for i in range(len(y_test))]))


def _confidence_stats(model: Any, X_test: pd.DataFrame) -> dict[str, float]:
    conf = np.max(model.predict_proba(X_test), axis=1)
    return {
        "confidence_mean": float(np.mean(conf)),
        "confidence_median": float(np.median(conf)),
        "confidence_p10": float(np.percentile(conf, 10)),
        "confidence_p90": float(np.percentile(conf, 90)),
    }


def _plot_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, classes: list[str], title: str, out: Path) -> None:
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, cmap="Blues", cbar=True)
    plt.title(title)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    plt.savefig(out, dpi=200)
    plt.close()


def _plot_topk_bar(df: pd.DataFrame, out: Path) -> None:
    plt.figure(figsize=(7, 4.5))
    sns.barplot(data=df, x="model", y="top3_accuracy", color="#3b82f6")
    plt.ylim(0, 1.05)
    plt.title("Top-3 Accuracy by Model")
    plt.xlabel("Model")
    plt.ylabel("Top-3 Accuracy")
    plt.tight_layout()
    plt.savefig(out, dpi=200)
    plt.close()


def train_eval_baselines(X: pd.DataFrame, y: np.ndarray) -> dict[str, Any]:
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=DEFAULT_TEST_SPLIT,
        random_state=42,
        stratify=y,
    )

    models: list[ModelArtifacts] = [
        ModelArtifacts("logistic_regression", LogisticRegression(max_iter=3000, n_jobs=None, random_state=42)),
        ModelArtifacts("random_forest", RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)),
    ]
    xgb = _try_get_xgb()
    if xgb is not None:
        models.append(ModelArtifacts("xgboost", xgb))

    rows: list[dict[str, Any]] = []
    conf_rows: list[dict[str, Any]] = []
    predictions: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    for m in models:
        m.estimator.fit(X_train, y_train)
        pred = m.estimator.predict(X_test)
        acc = float(accuracy_score(y_test, pred))
        prec, rec, f1, _ = precision_recall_fscore_support(y_test, pred, average="macro", zero_division=0)
        top3 = _top3_accuracy(m.estimator, X_test, y_test)
        rows.append(
            {
                "model": m.name,
                "accuracy": acc,
                "macro_precision": float(prec),
                "macro_recall": float(rec),
                "macro_f1": float(f1),
                "top3_accuracy": top3,
            }
        )
        conf_row = {"model": m.name, **_confidence_stats(m.estimator, X_test)}
        conf_rows.append(conf_row)
        predictions[m.name] = (y_test, pred)

    return {
        "performance": pd.DataFrame(rows),
        "confidence": pd.DataFrame(conf_rows),
        "predictions": predictions,
    }


def run(run_dir: Path) -> dict[str, Any]:
    notes: list[str] = []
    tables_dir = run_dir / "tables"
    plots_dir = run_dir / "plots"

    try:
        X, y, le = load_dataset_xlsx(DATASET_PATH)
    except Exception as exc:
        notes.append(f"Model metrics unavailable: failed to load dataset ({exc}).")
        return {"notes": notes, "available": False}

    try:
        result = train_eval_baselines(X, y)
        perf_df: pd.DataFrame = result["performance"]
        conf_df: pd.DataFrame = result["confidence"]
        preds: dict[str, tuple[np.ndarray, np.ndarray]] = result["predictions"]

        write_csv(perf_df, tables_dir / "model_performance.csv")
        write_md_table(perf_df, tables_dir / "model_performance.md", "Model Performance")

        write_csv(conf_df, tables_dir / "confidence_distribution.csv")
        write_md_table(conf_df, tables_dir / "confidence_distribution.md", "Confidence Distribution")

        for model_name, (y_true, y_pred) in preds.items():
            _plot_confusion_matrix(
                y_true=y_true,
                y_pred=y_pred,
                classes=list(le.classes_),
                title=f"Confusion Matrix: {model_name}",
                out=plots_dir / f"confusion_matrix_{model_name}.png",
            )

        _plot_topk_bar(perf_df, plots_dir / "topk_accuracy_bar.png")
        return {"notes": notes, "available": True}
    except Exception as exc:
        notes.append(f"Model metrics generation failed: {exc}")
        return {"notes": notes, "available": False}
