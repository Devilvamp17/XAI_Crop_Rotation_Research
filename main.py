from __future__ import annotations

from functools import lru_cache
import math
import os
from pathlib import Path
from typing import Any

import joblib
import lime.lime_tabular
import numpy as np
import pandas as pd
import shap
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

PROJECT_ROOT = Path(__file__).resolve().parent
FEATURE_COLUMNS = ["N", "P", "K", "temperature", "humidity", "ph"]
DEFAULT_MODELS = ["logistic_regression", "random_forest", "xgboost"]
LIME_KERNEL_WIDTH_MULTIPLIER = 0.75
LIME_KERNEL_WIDTH = LIME_KERNEL_WIDTH_MULTIPLIER * math.sqrt(len(FEATURE_COLUMNS))
LIME_NUM_SAMPLES = max(5000, int(os.getenv("LIME_NUM_SAMPLES", "5000")))
LIME_DISCRETIZE_CONTINUOUS = False


class CropFeatures(BaseModel):
    N: float = Field(..., description="Nitrogen value")
    P: float = Field(..., description="Phosphorous value")
    K: float = Field(..., description="Potassium value")
    temperature: float
    humidity: float
    ph: float


class PredictRequest(BaseModel):
    input: CropFeatures
    models: list[str] = Field(default_factory=lambda: DEFAULT_MODELS.copy())
    top_k: int = Field(default=3, ge=1, le=10)

    @model_validator(mode="after")
    def validate_models(self) -> "PredictRequest":
        allowed = set(DEFAULT_MODELS)
        bad = [m for m in self.models if m not in allowed]
        if bad:
            raise ValueError(f"Unsupported models requested: {bad}")
        return self


@lru_cache(maxsize=1)
def load_resources() -> dict[str, Any]:
    lr_model = joblib.load(PROJECT_ROOT / "models/logistic_model.pkl")
    rf_model = joblib.load(PROJECT_ROOT / "models/random_forest_model.pkl")
    xgb_model = joblib.load(PROJECT_ROOT / "models/xgb_model.pkl")
    label_encoder = joblib.load(PROJECT_ROOT / "models/label_encoder.pkl")

    full_dataset = pd.read_excel(PROJECT_ROOT / "Crop_recommendation.xlsx")
    x_train = full_dataset[FEATURE_COLUMNS]
    background = shap.sample(x_train, 100, random_state=42)

    shap_lr = shap.LinearExplainer(lr_model, background)
    shap_rf = shap.TreeExplainer(rf_model)
    shap_xgb = shap.TreeExplainer(xgb_model)

    class_names = label_encoder.inverse_transform(np.asarray(xgb_model.classes_, dtype=int)).tolist()
    lime_explainer = lime.lime_tabular.LimeTabularExplainer(
        training_data=x_train.values,
        feature_names=FEATURE_COLUMNS,
        class_names=class_names,
        mode="classification",
        discretize_continuous=LIME_DISCRETIZE_CONTINUOUS,
        kernel_width=LIME_KERNEL_WIDTH,
    )

    return {
        "models": {
            "logistic_regression": {"model": lr_model, "shap": shap_lr},
            "random_forest": {"model": rf_model, "shap": shap_rf},
            "xgboost": {"model": xgb_model, "shap": shap_xgb},
        },
        "label_encoder": label_encoder,
        "lime_explainer": lime_explainer,
    }


def _extract_shap_for_class(
    shap_values: Any, expected_value: Any, class_index: int
) -> tuple[np.ndarray, float]:
    if isinstance(shap_values, list):
        values = np.array(shap_values[class_index][0], dtype=float)
        base = expected_value[class_index]
    elif isinstance(shap_values, np.ndarray):
        if shap_values.ndim == 3:
            values = np.array(shap_values[0, :, class_index], dtype=float)
        elif shap_values.ndim == 2:
            values = np.array(shap_values[0], dtype=float)
        elif shap_values.ndim == 1:
            values = np.array(shap_values, dtype=float)
        else:
            raise ValueError(f"Unsupported SHAP ndarray shape: {shap_values.shape}")

        if isinstance(expected_value, (list, np.ndarray)):
            base = expected_value[class_index]
        else:
            base = expected_value
    else:
        raise ValueError(f"Unsupported SHAP output type: {type(shap_values)}")

    return values, float(base)


def _preprocess_features_df(model: Any, features_df: pd.DataFrame) -> pd.DataFrame:
    _ = model
    return features_df[FEATURE_COLUMNS].copy()


def _predict_proba_from_original_space(model: Any, arr: np.ndarray) -> np.ndarray:
    arr_2d = np.asarray(arr, dtype=float)
    if arr_2d.ndim == 1:
        arr_2d = arr_2d.reshape(1, -1)
    if arr_2d.ndim != 2:
        raise ValueError(f"LIME predict_fn expects 2D array, got shape={arr_2d.shape}")
    if arr_2d.shape[1] != len(FEATURE_COLUMNS):
        raise ValueError(
            f"LIME predict_fn expects {len(FEATURE_COLUMNS)} features, got {arr_2d.shape[1]}"
        )
    arr_df = pd.DataFrame(arr_2d, columns=FEATURE_COLUMNS)
    arr_df = _preprocess_features_df(model, arr_df)
    probs = np.asarray(model.predict_proba(arr_df), dtype=float)
    if probs.ndim != 2:
        raise ValueError(f"predict_proba must return 2D array, got shape={probs.shape}")
    if probs.shape[0] != arr_2d.shape[0]:
        raise ValueError(
            f"predict_proba row mismatch: input={arr_2d.shape[0]} output={probs.shape[0]}"
        )
    return probs


def build_lime_predict_fn(model: Any):
    def _predict_fn(arr: np.ndarray) -> np.ndarray:
        return _predict_proba_from_original_space(model, arr)

    return _predict_fn


def _predict_one_model(
    model_name: str,
    model: Any,
    shap_explainer: Any,
    lime_explainer: lime.lime_tabular.LimeTabularExplainer,
    label_encoder: Any,
    input_df: pd.DataFrame,
    top_k: int,
) -> dict[str, Any]:
    prediction = model.predict(input_df)
    prediction_proba = model.predict_proba(input_df)
    predicted_class = int(prediction[0])
    predicted_crop = label_encoder.inverse_transform(prediction)[0]
    confidence = float(np.max(prediction_proba[0]))

    top_indices = np.argsort(prediction_proba[0])[::-1][:top_k]
    top_crops = label_encoder.inverse_transform(top_indices)
    top_scores = prediction_proba[0][top_indices]
    top3 = [
        {"rank": idx + 1, "crop": str(top_crops[idx]), "confidence": float(top_scores[idx])}
        for idx in range(len(top_indices))
    ]

    predicted_class_index = int(np.where(model.classes_ == predicted_class)[0][0])
    shap_values = shap_explainer.shap_values(input_df)
    shap_selected, shap_base = _extract_shap_for_class(
        shap_values=shap_values,
        expected_value=shap_explainer.expected_value,
        class_index=predicted_class_index,
    )
    shap_feature_values = {
        feature: float(value) for feature, value in zip(FEATURE_COLUMNS, shap_selected, strict=True)
    }

    shap_sorted = sorted(
        (
            {"feature": feature, "value": value, "abs_value": abs(value)}
            for feature, value in shap_feature_values.items()
        ),
        key=lambda x: x["abs_value"],
        reverse=True,
    )

    lime_exp = lime_explainer.explain_instance(
        data_row=input_df.iloc[0].values,
        predict_fn=build_lime_predict_fn(model),
        num_features=len(FEATURE_COLUMNS),
        num_samples=LIME_NUM_SAMPLES,
        labels=(predicted_class_index,),
    )
    lime_items = [
        {"feature": feature_rule, "weight": float(weight)}
        for feature_rule, weight in lime_exp.as_list(label=predicted_class_index)
    ]

    return {
        "model": model_name,
        "prediction": {
            "crop": str(predicted_crop),
            "predicted_class": predicted_class,
            "confidence": confidence,
        },
        "top3": top3,
        "shap": {
            "base_value": shap_base,
            "values": shap_feature_values,
            "sorted_by_abs": shap_sorted,
        },
        "lime": {
            "class_index": predicted_class_index,
            "explanations": lime_items,
        },
        "curves": {
            "topk_confidence": {
                "x": [str(c) for c in top_crops.tolist()],
                "y": [float(s) for s in top_scores.tolist()],
            }
        },
    }


app = FastAPI(title="Crop Recommendation XAI API", version="1.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict")
def predict(payload: PredictRequest | CropFeatures) -> dict[str, Any]:
    try:
        resources = load_resources()

        if isinstance(payload, CropFeatures):
            features = payload.model_dump()
            selected_models = DEFAULT_MODELS
            top_k = 3
        else:
            features = payload.input.model_dump()
            selected_models = payload.models
            top_k = payload.top_k

        input_df = pd.DataFrame([features], columns=FEATURE_COLUMNS)

        label_encoder = resources["label_encoder"]
        lime_explainer = resources["lime_explainer"]

        model_outputs = {}
        for model_name in selected_models:
            artifact = resources["models"][model_name]
            model_outputs[model_name] = _predict_one_model(
                model_name=model_name,
                model=artifact["model"],
                shap_explainer=artifact["shap"],
                lime_explainer=lime_explainer,
                label_encoder=label_encoder,
                input_df=input_df,
                top_k=top_k,
            )

        return {
            "input": features,
            "models": model_outputs,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction pipeline failed: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
