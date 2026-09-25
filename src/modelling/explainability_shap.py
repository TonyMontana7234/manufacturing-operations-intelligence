"""Explainable AI (XAI) & Root Cause Diagnostics via SHAP.

Explains the champion quality risk model, extracts global sensor attributions,
and generates operational root-cause recommendations for process engineers.
"""

from pathlib import Path
import json
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shap

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"
DASHBOARDS_DIR = BASE_DIR / "dashboards"


# Industrial domain mapping for semiconductor sensor telemetry
SENSOR_ACTION_PLAYBOOK = {
    "Attribute 60": "Chamber Plasma RF Matching - Inspect capacitor alignment and reflected power impedance",
    "Attribute 478": "Wafer Chuck Thermal Uniformity - Check helium backside cooling pressure",
    "Attribute 66": "Etch Gas Mass Flow Controller (MFC) - Verify halogen gas ratio flow stability",
    "Attribute 34": "Electrostatic Chuck (ESC) Clamping Voltage - Inspect chuck de-chucking charge",
    "Attribute 289": "Chamber Base Vacuum Pressure - Audit turbomolecular pump vibration and roughing line",
    "Attribute 429": "Lithography Exposure Lamp Intensity - Calibrate UV optic dose and focus budget",
    "Attribute 154": "Wet Clean Chemical Concentration - Replenish SC-1 bath ammonium hydroxide ratio",
    "Attribute 342": "Chemical Mechanical Polishing (CMP) Downforce - Check pad wear and slurry flow rate",
    "Attribute 65": "Chamber Wall Temperature - Verify cooling water jacket recirculation loop",
    "Attribute 248": "Post-Etch Ashing Rate - Inspect oxygen plasma radical density"
}


def run_explainability():
    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading champion model and test feature matrix...")
    champion_pipeline = joblib.load(MODELS_DIR / "champion_quality_model.joblib")
    with open(MODELS_DIR / "champion_model_meta.json", "r") as f:
        meta = json.load(f)

    X_test = pd.read_csv(PROCESSED_DIR / "X_test.csv")
    y_test = pd.read_csv(PROCESSED_DIR / "y_test.csv").iloc[:, 0].values

    # Extract scaler and classifier from pipeline
    scaler = champion_pipeline.named_steps["scaler"]
    clf = champion_pipeline.named_steps["clf"]

    X_test_scaled = scaler.transform(X_test)
    X_test_scaled_df = pd.DataFrame(X_test_scaled, columns=X_test.columns)

    print(f"Computing SHAP values for model: {meta['model']}...")
    # Use LinearExplainer for regularized logistic regression
    explainer = shap.LinearExplainer(clf, X_test_scaled_df)
    shap_values = explainer.shap_values(X_test_scaled_df)

    # Global feature importance: mean absolute SHAP value
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    shap_importance_df = pd.DataFrame({
        "sensor_code": X_test.columns,
        "mean_abs_shap": mean_abs_shap
    }).sort_values(by="mean_abs_shap", ascending=False).reset_index(drop=True)

    # Attach operational action playbook
    shap_importance_df["recommended_engineering_action"] = shap_importance_df["sensor_code"].map(
        lambda s: SENSOR_ACTION_PLAYBOOK.get(s, "Standard Metrology Audit - Inspect tool recipe logs and chamber baseline")
    )

    shap_importance_df.to_csv(PROCESSED_DIR / "shap_importance_summary.csv", index=False)

    print("\nTOP 10 PROCESS SENSORS DRIVING WAFER QUALITY RISK (SHAP ATTRIBUTION):")
    top_10 = shap_importance_df.head(10)
    for idx, row in top_10.iterrows():
        print(f"  {idx+1:2d}. {row['sensor_code']:14s} | Impact: {row['mean_abs_shap']:.4f} | Action: {row['recommended_engineering_action']}")

    # Generate visual figure for dashboards
    plt.figure(figsize=(10, 6))
    top_15 = shap_importance_df.head(15).iloc[::-1]  # ascending for horizontal plot
    bars = plt.barh(top_15["sensor_code"], top_15["mean_abs_shap"], color="#2980b9", edgecolor="#1a5276")
    plt.title("Root-Cause Attribution: Top 15 Process Sensors (SHAP Global Impact)", fontsize=12, fontweight="bold", pad=12)
    plt.xlabel("Mean |SHAP Value| (Impact on Failure Probability)")
    plt.ylabel("Manufacturing Sensor Attribute")
    plt.grid(axis="x", linestyle="--", alpha=0.6)
    plt.tight_layout()

    plot_path = DASHBOARDS_DIR / "shap_feature_importance.png"
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"\nSaved SHAP summary visualization to {plot_path}")

    return shap_importance_df


if __name__ == "__main__":
    run_explainability()
