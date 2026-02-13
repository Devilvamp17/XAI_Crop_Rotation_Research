# Crop Recommendation System

This project is a **Crop Recommendation System** that predicts suitable crops based on input features. It includes model development, explainable AI analysis, a Streamlit app, and a FastAPI service for programmatic inference.

---

## Project Structure
```
├── models/ # Saved trained models
├── results/ # Model evaluation results and visualizations
├── xai/ # Explainable AI outputs (SHAP, LIME)
├── .python-version # Python version used
├── Crop_recommendation.xlsx # Dataset
├── main.ipynb # Main notebook for data processing, model development, and evaluation
├── model.ipynb # Optional notebook for specific model experiments
├── main.py # FastAPI app for crop prediction + XAI response
├── stream.py # Streamlit app for inference and visualization
├── test.py # Extensive API validation script
├── test_api.py # API schema and behavior checks
├── simplescreenrecorder-...mkv # Screen recording of the platform
├── requirments.txt # Python dependencies
└── README.md # Project documentation
```

---

## Features

### Machine Learning Models
- **Logistic Regression** – Baseline model for crop classification.
- **Random Forest** – Robust ensemble tree-based classifier.
- **XGBoost** – Gradient boosting model for high performance.
- **Ensemble Models** – Combines predictions using blending or voting strategies for improved accuracy.

### Explainable AI (XAI)
- **SHAP (SHapley Additive exPlanations)**
  - Provides global and local feature contribution analysis.
  - Helps understand how each input feature affects predictions.
- **LIME (Local Interpretable Model-agnostic Explanations)**
  - Generates local explanations for individual predictions.
  - Useful for debugging models and building trust in predictions.
- All XAI outputs are stored in the `xai/` folder for reference.

### Streamlit Web Platform
- Interactive user interface for real-time crop recommendations.
- Supports multiple model predictions and comparison.
- Visualization of feature importance and explanation results (SHAP & LIME).
- Designed for ease of use, allowing non-technical users to explore model outputs.

### FastAPI Service
- Exposes prediction APIs for integration with clients/tools.
- Returns output for all 3 models: Logistic Regression, Random Forest, and XGBoost.
- Includes predicted crop, confidence, top-3 crops, SHAP contributions, and LIME explanations.

---

## Installation

1. Clone the repository:
  ```
  git clone <repository-url>
  cd <repository-folder>
  ```
2. Install dependencies:
  ```
  pip install -r requirments.txt
  ```

---

## Run Streamlit App
```
streamlit run stream.py
```

- Input crop-related features
- View predictions from multiple models
- Explore model explanation using SHAP and LIME

---

## Run API
```
uvicorn main:app --host 0.0.0.0 --port 8000
```

### API Endpoints
- `GET /health`  
  Returns service status.
- `POST /predict`  
  Returns predictions and explanations for all three models.

### Sample Request
`POST /predict`
```json
{
  "N": 90,
  "P": 42,
  "K": 43,
  "temperature": 25.6,
  "humidity": 71.4,
  "ph": 6.4
}
```

### Sample Response (shape)
```json
{
  "input": {
    "N": 90.0,
    "P": 42.0,
    "K": 43.0,
    "temperature": 25.6,
    "humidity": 71.4,
    "ph": 6.4
  },
  "models": {
    "logistic_regression": {
      "model": "logistic_regression",
      "prediction": {"crop": "jute", "predicted_class": 8, "confidence": 0.85},
      "top3": [{"rank": 1, "crop": "jute", "confidence": 0.85}],
      "shap": {"base_value": 0.12, "values": {}, "sorted_by_abs": []},
      "lime": {"class_index": 8, "explanations": [{"feature": "humidity > 70.0", "weight": 0.21}]}
    },
    "random_forest": {},
    "xgboost": {}
  }
}
```

### Quick cURL Test
```bash
curl --json '{"N":90,"P":42,"K":43,"temperature":25.6,"humidity":71.4,"ph":6.4}' http://127.0.0.1:8000/predict
```

### Run API Tests
```bash
python test.py
python test_api.py
```

---

## Dependencies
``` 
fastapi>=0.129.0
uvicorn[standard]>=0.40.0
httpx>=0.28.1
streamlit>=1.54.0
pandas>=2.3.3
numpy<2.4
matplotlib>=3.10.8
scikit-learn==1.6.1
xgboost>=3.2.0
shap>=0.43
lime>=0.2.0.1
openpyxl>=3.1.5
seaborn>=0.13.2
numba>=0.61
torch>=2.10.0
ipykernel>=7.2.0
```

---

## Pipeline Overview

1. **Data Preprocessing**
   - Handling missing values and outliers.
   - Scaling numerical features and encoding categorical features.
   - Feature engineering to improve model performance.

2. **Model Development**
   - Train Logistic Regression, Random Forest, XGBoost, and Ensemble models.
   - Evaluate models using metrics such as Accuracy, F1-score, Confusion Matrix, and Classification Report.
   - Save trained models in `models/` for reuse.

3. **Explainable AI Analysis**
   - Generate SHAP summary and force plots for global and local interpretation.
   - Generate LIME explanations for individual predictions.
   - Store visualizations and results in `xai/`.

4. **Streamlit Web Application**
   - Users input soil and environmental features such as Nitrogen, Phosphorus, Potassium, pH, rainfall, and temperature.
   - App predicts suitable crops using multiple models.
   - Visualizes model outputs and XAI explanations in an interactive interface.

5. **Results**
   - Model evaluation results including metrics and plots stored in `results/`.
   - Screen recordings available for demonstration in `simplescreenrecorder-...mkv`.

---

## XAI Analysis
- **SHAP**: Visualizes feature contributions for each prediction.
- **LIME**: Provides local interpretable explanations for model outputs.
- All XAI results are stored in the `xai/` folder for reference.

---

## Screen Recording
- `simplescreenrecorder-2025-06-08_12.39.29.mkv` demonstrates the functionality of the platform and how users can interact with the models via the Streamlit app.

---

## Contributing
1. Fork the repository
2. Create a new branch
   ```
   git checkout -b feature-branch
   ```
3. Commit your changes
   ```
   git commit -m 'Add new feature'
   ```
4. Push to the branch
   ```
   git push origin feature-branch
   ```
5. Create a pull request

---
 
## License

This project is licensed under the MIT License.

