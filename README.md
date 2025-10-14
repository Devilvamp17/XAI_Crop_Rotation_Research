# Crop Recommendation System

This project is a **Crop Recommendation System** that predicts suitable crops based on input features. It includes model development, explainable AI analysis, and a Streamlit-based platform for inference and visualization.

---

## Project Structure
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

## Jupyter Notebook
- `main.ipynb` contains the full pipeline:
  - Data preprocessing
  - Model training and evaluation
  - XAI analysis
- `model.ipynb` (optional) contains additional experiments with individual models.

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
