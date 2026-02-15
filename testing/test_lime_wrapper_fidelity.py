from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import FEATURE_COLUMNS, build_lime_predict_fn, load_resources
from xai_eval.evaluate import run_evaluation


def test_lime_predict_wrapper_shape_and_class_mapping() -> None:
    resources = load_resources()
    model = resources["models"]["xgboost"]["model"]
    label_encoder = resources["label_encoder"]

    data = pd.read_excel(Path("Crop_recommendation.xlsx"))
    x = data[FEATURE_COLUMNS].head(4)

    predict_fn = build_lime_predict_fn(model)
    probs = predict_fn(x.values)

    assert probs.shape == (4, len(model.classes_))

    pred_idx = int(np.argmax(probs[0]))
    pred_class = model.classes_[pred_idx]
    pred_label_from_idx = label_encoder.inverse_transform(np.asarray([pred_class], dtype=int))[0]

    model_pred_class = int(model.predict(x.iloc[[0]])[0])
    model_pred_label = label_encoder.inverse_transform(np.asarray([model_pred_class], dtype=int))[0]
    assert pred_label_from_idx == model_pred_label


def test_lime_fidelity_report_and_status(tmp_path: Path) -> None:
    report = run_evaluation(out_dir=tmp_path)
    curves = json.loads((tmp_path / "curves.json").read_text(encoding="utf-8"))

    lime = report.get("lime", {})
    assert "mean_fidelity_r2" in lime
    assert "median_fidelity_r2" in lime
    assert "fraction_r2_gt_0" in lime
    assert lime.get("status") in {"reliable", "unreliable"}

    fidelity_list = curves.get("lime_fidelity_r2_list")
    assert isinstance(fidelity_list, list)


if __name__ == "__main__":
    test_lime_predict_wrapper_shape_and_class_mapping()
    with TemporaryDirectory() as d:
        test_lime_fidelity_report_and_status(Path(d))
    print("LIME wrapper/fidelity tests passed.")
