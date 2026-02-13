import streamlit as st
import pandas as pd
import numpy as np
import joblib
import shap
import matplotlib.pyplot as plt
import lime.lime_tabular
import streamlit.components.v1 as components
import tempfile
import os
from pathlib import Path

st.set_page_config(
    page_title="Crop Prediction with XAI",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

PROJECT_ROOT = Path(__file__).resolve().parent

# --- Load Models and Explainers ---
@st.cache_resource
def load_resources():
    try:
        lr_model = joblib.load(PROJECT_ROOT / 'models/logistic_model.pkl')
        rf_model = joblib.load(PROJECT_ROOT / 'models/random_forest_model.pkl')
        xgb_model = joblib.load(PROJECT_ROOT / 'models/xgb_model.pkl')
        label_encoder = joblib.load(PROJECT_ROOT / 'models/label_encoder.pkl')

        shap_explainer_lr = joblib.load(PROJECT_ROOT / 'xai/shap_logistic.pkl')
        shap_explainer_rf = joblib.load(PROJECT_ROOT / 'xai/shap_rf.pkl')
        try:
            shap_explainer_xgb = joblib.load(PROJECT_ROOT / 'xai/shap_xgb.pkl')
        except Exception as shap_xgb_err:
            st.warning(f"XGBoost SHAP explainer file invalid/unavailable: {shap_xgb_err}. Rebuilding...")
            shap_explainer_xgb = shap.TreeExplainer(xgb_model)
            joblib.dump(shap_explainer_xgb, PROJECT_ROOT / 'xai/shap_xgb.pkl')

        full_dataset = pd.read_excel(PROJECT_ROOT / 'Crop_recommendation.xlsx')
        feature_cols = ['N', 'P', 'K', 'temperature', 'humidity', 'ph']
        X_train = full_dataset[feature_cols]

        lime_explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=X_train.values,
            feature_names=X_train.columns.tolist(),
            class_names=label_encoder.classes_,
            mode="classification"
        )

        return lr_model, rf_model, xgb_model, label_encoder, shap_explainer_lr, shap_explainer_rf, shap_explainer_xgb, lime_explainer, X_train

    except Exception as e:
        st.error(f"❌ Error loading resources: {e}")
        raise

# Load all models and explainers
lr_model, rf_model, xgb_model, label_encoder, shap_explainer_lr, shap_explainer_rf, shap_explainer_xgb, lime_explainer, X_train = load_resources()

# Emoji dictionary for predicted crops
crop_emojis = {
    "rice": "🍚", "wheat": "🌾", "maize": "🌽", "mango": "🥭", "banana": "🍌",
    "coffee": "☕", "cotton": "🧵", "apple": "🍎", "grapes": "🍇"
}

# Sidebar: What-If Tool sliders
st.sidebar.header('🧪 What-If Tool: Adjust Features')
def user_input_features():
    N = st.sidebar.slider('Nitrogen (N) in kg/ha', 0, 140, 90)
    P = st.sidebar.slider('Phosphorous (P) in kg/ha', 5, 145, 42)
    K = st.sidebar.slider('Potassium (K) in kg/ha', 5, 205, 43)
    temperature = st.sidebar.slider('Temperature in °C', 8.0, 44.0, 25.6)
    humidity = st.sidebar.slider('Relative Humidity in %', 14.0, 100.0, 71.4)
    ph = st.sidebar.slider('pH of the soil', 3.5, 9.9, 6.4)

    data = {'N': N, 'P': P, 'K': K, 'temperature': temperature, 'humidity': humidity, 'ph': ph}
    return pd.DataFrame(data, index=[0])

input_df = user_input_features()

# Main interface
st.title('🌾 Crop Recommendation with Explainable AI (XAI)')
st.write("This application predicts the best crop to grow and explains why, using SHAP and LIME.")

st.subheader('📥 Your Input Features')
st.dataframe(input_df, width="stretch")

if st.button('Predict and Compare All Models', type="primary"):
    with st.spinner("Running predictions and generating explanations..."):
        models_to_run = {
            'Logistic Regression': (lr_model, shap_explainer_lr),
            'Random Forest': (rf_model, shap_explainer_rf),
            'XGBoost': (xgb_model, shap_explainer_xgb)
        }

        predictions = []
        confidences = []

        cols = st.columns(len(models_to_run))

        for col, (model_name, (model, shap_explainer)) in zip(cols, models_to_run.items()):
            with col:
                st.subheader(model_name)

                prediction = model.predict(input_df)
                prediction_proba = model.predict_proba(input_df)
                predicted_crop = label_encoder.inverse_transform(prediction)[0]
                confidence = np.max(prediction_proba)

                predictions.append(predicted_crop)
                confidences.append(confidence)

                # 🌱 Emoji-enhanced prediction
                emoji = crop_emojis.get(predicted_crop.lower(), "🌱")
                st.success(f"{emoji} **{predicted_crop.capitalize()}**")

                # 🌟 Show top-3 crop suggestions
                st.markdown("#### 🌿 Top 3 Crop Suggestions:")
                top_n = 3
                top_indices = np.argsort(prediction_proba[0])[::-1][:top_n]
                top_crops = label_encoder.inverse_transform(top_indices)
                top_scores = prediction_proba[0][top_indices]

                for i in range(top_n):
                    emoji = crop_emojis.get(top_crops[i].lower(), "🌱")
                    st.markdown(f"{i+1}. {emoji} **{top_crops[i]}** — Confidence: `{top_scores[i]:.2f}`")

                # SHAP Explanation
                with st.expander("🔍 SHAP Explanation", expanded=True):
                    shap_vals = shap_explainer.shap_values(input_df)
                    expected_val = shap_explainer.expected_value
                    predicted_class_index = np.where(model.classes_ == prediction[0])[0][0]

                    if isinstance(shap_vals, list):
                        shap_vals_selected = shap_vals[predicted_class_index][0]
                        expected_val_selected = expected_val[predicted_class_index]
                    elif isinstance(shap_vals, np.ndarray):
                        shap_vals_selected = shap_vals[0] if shap_vals.ndim == 2 else shap_vals[0, :, predicted_class_index]
                        expected_val_selected = expected_val[predicted_class_index] if isinstance(expected_val, (list, np.ndarray)) else expected_val
                    else:
                        st.error("Unsupported SHAP value format.")
                        st.stop()

                    # Waterfall plot
                    st.markdown("**Waterfall Plot (Static)**")
                    explanation = shap.Explanation(
                        values=shap_vals_selected,
                        base_values=expected_val_selected,
                        data=input_df.iloc[0].values,
                        feature_names=input_df.columns.tolist()
                    )
                    fig_shap, ax = plt.subplots()
                    shap.plots.waterfall(explanation, show=False)
                    st.pyplot(fig_shap)
                    plt.close(fig_shap)

                    # Force plot
                    st.markdown("**Force Plot (Interactive)**")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmpfile:
                        shap.save_html(tmpfile.name,
                            shap.force_plot(
                                base_value=expected_val_selected,
                                shap_values=shap_vals_selected,
                                features=input_df.iloc[0],
                                feature_names=input_df.columns.tolist(),
                                matplotlib=False
                            )
                        )
                        components.html(open(tmpfile.name, 'r', encoding='utf-8').read(), height=300)
                        os.unlink(tmpfile.name)

                # LIME Explanation
                with st.expander("🧠 LIME Explanation"):
                    lime_exp = lime_explainer.explain_instance(
                        data_row=input_df.iloc[0].values,
                        predict_fn=model.predict_proba,
                        num_features=len(input_df.columns),
                        num_samples=5000,
                        labels=(predicted_class_index,)
                    )
                    fig_lime = lime_exp.as_pyplot_figure(label=predicted_class_index)
                    plt.tight_layout()
                    st.pyplot(fig_lime)
                    plt.close(fig_lime)

                # Feature Importance
                with st.expander("📊 Feature Importance (Model-based)"):
                    if hasattr(model, 'feature_importances_'):
                        importances = model.feature_importances_
                        sorted_idx = np.argsort(importances)[::-1]
                        feature_names = input_df.columns[sorted_idx]
                        sorted_importances = importances[sorted_idx]

                        fig_feat, ax_feat = plt.subplots()
                        ax_feat.barh(feature_names[::-1], sorted_importances[::-1])
                        ax_feat.set_xlabel("Importance Score")
                        ax_feat.set_title("Feature Importance")
                        st.pyplot(fig_feat)
                        plt.close(fig_feat)

                    elif hasattr(model, 'coef_'):
                        coef_vals = np.abs(model.coef_[0])
                        sorted_idx = np.argsort(coef_vals)[::-1]
                        feature_names = input_df.columns[sorted_idx]
                        sorted_coefs = coef_vals[sorted_idx]

                        fig_coef, ax_coef = plt.subplots()
                        ax_coef.barh(feature_names[::-1], sorted_coefs[::-1])
                        ax_coef.set_xlabel("Coefficient Magnitude")
                        ax_coef.set_title("Logistic Regression Coefficients")
                        st.pyplot(fig_coef)
                        plt.close(fig_coef)
                    else:
                        st.info("Feature importance not available for this model.")

        # Confidence comparison plot
        st.subheader("📈 Confidence Score Across Models")
        fig_conf, ax_conf = plt.subplots()
        bars = ax_conf.bar(models_to_run.keys(), confidences, color=['#66c2a5', '#fc8d62', '#8da0cb'])
        ax_conf.set_ylim(0, 1.1)
        ax_conf.set_ylabel("Confidence", fontsize=12)
        ax_conf.set_title("Model Confidence Levels", fontsize=14)

        for bar, conf in zip(bars, confidences):
            ax_conf.text(bar.get_x() + bar.get_width()/2, conf + 0.02, f"{conf:.2f}", ha='center', fontsize=10)
        st.pyplot(fig_conf)
        plt.close(fig_conf)

st.markdown("---")
st.markdown("🔬 Developed as part of Explainable AI for Crop Prediction.")
