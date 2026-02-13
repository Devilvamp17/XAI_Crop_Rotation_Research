from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import lime.lime_tabular
import numpy as np
import pandas as pd
import shap
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent
FEATURE_COLUMNS = ["N", "P", "K", "temperature", "humidity", "ph"]
TOP_N = 3


class CropRequest(BaseModel):
    N: float = Field(..., description="Nitrogen value")
    P: float = Field(..., description="Phosphorous value")
    K: float = Field(..., description="Potassium value")
    temperature: float
    humidity: float
    ph: float


@lru_cache(maxsize=1)
def load_resources() -> dict[str, Any]:
    lr_model = joblib.load(PROJECT_ROOT / "models/logistic_model.pkl")
    rf_model = joblib.load(PROJECT_ROOT / "models/random_forest_model.pkl")
    xgb_model = joblib.load(PROJECT_ROOT / "models/xgb_model.pkl")
    label_encoder = joblib.load(PROJECT_ROOT / "models/label_encoder.pkl")

    full_dataset = pd.read_excel(PROJECT_ROOT / "Crop_recommendation.xlsx")
    x_train = full_dataset[FEATURE_COLUMNS]
    background = shap.sample(x_train, 100, random_state=42)

    # Build explainers from live models to avoid pickle incompatibility across SHAP versions.
    shap_lr = shap.LinearExplainer(lr_model, background)
    shap_rf = shap.TreeExplainer(rf_model)
    shap_xgb = shap.TreeExplainer(xgb_model)

    lime_explainer = lime.lime_tabular.LimeTabularExplainer(
        training_data=x_train.values,
        feature_names=FEATURE_COLUMNS,
        class_names=label_encoder.classes_.tolist(),
        mode="classification",
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


def _predict_one_model(
    model_name: str,
    model: Any,
    shap_explainer: Any,
    lime_explainer: lime.lime_tabular.LimeTabularExplainer,
    label_encoder: Any,
    input_df: pd.DataFrame,
) -> dict[str, Any]:
    prediction = model.predict(input_df)
    prediction_proba = model.predict_proba(input_df)
    predicted_class = int(prediction[0])
    predicted_crop = label_encoder.inverse_transform(prediction)[0]
    confidence = float(np.max(prediction_proba[0]))

    top_indices = np.argsort(prediction_proba[0])[::-1][:TOP_N]
    top_crops = label_encoder.inverse_transform(top_indices)
    top_scores = prediction_proba[0][top_indices]
    top3 = [
        {"rank": idx + 1, "crop": str(top_crops[idx]), "confidence": float(top_scores[idx])}
        for idx in range(TOP_N)
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

    def predict_proba_from_array(arr: np.ndarray) -> np.ndarray:
        arr_df = pd.DataFrame(arr, columns=FEATURE_COLUMNS)
        return model.predict_proba(arr_df)

    lime_exp = lime_explainer.explain_instance(
        data_row=input_df.iloc[0].values,
        predict_fn=predict_proba_from_array,
        num_features=len(FEATURE_COLUMNS),
        num_samples=5000,
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
    }


app = FastAPI(title="Crop Recommendation XAI API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict")
def predict(payload: CropRequest) -> dict[str, Any]:
    try:
        resources = load_resources()
        input_df = pd.DataFrame([payload.model_dump()], columns=FEATURE_COLUMNS)

        label_encoder = resources["label_encoder"]
        lime_explainer = resources["lime_explainer"]

        model_outputs = {}
        for model_name, artifact in resources["models"].items():
            model_outputs[model_name] = _predict_one_model(
                model_name=model_name,
                model=artifact["model"],
                shap_explainer=artifact["shap"],
                lime_explainer=lime_explainer,
                label_encoder=label_encoder,
                input_df=input_df,
            )

        return {
            "input": payload.model_dump(),
            "models": model_outputs,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction pipeline failed: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
