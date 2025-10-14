# Crop Recommendation System

This project is a **Crop Recommendation System** that predicts suitable crops based on input features. It includes model development, explainable AI analysis, and a Streamlit-based platform for inference and visualization.

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
├── stream.py # Streamlit app for inference and visualization
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

## Dependencies
```
streamlit>=1.20.0
pandas>=2.0.0
numpy>=1.24.0
joblib>=1.3.0
shap>=0.42.0
matplotlib>=3.7.0
lime>=0.2.2.1
seaborn>=0.12.2
scikit-learn>=1.3.0
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

