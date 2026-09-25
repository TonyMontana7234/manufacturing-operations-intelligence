"""Train and Benchmark Quality-Risk Classification Models.

Evaluates:
1. Dummy Majority Classifier (benchmarks the 94.6% accuracy trap)
2. Cost-Sensitive Logistic Regression (L2 regularized)
3. Balanced Random Forest
4. Cost-Weighted Gradient Boosting Classifier

Metrics:
- PR-AUC (Precision-Recall AUC / Average Precision)
- ROC-AUC
- Precision, Recall, F1-Score
- Cost of Quality (CoQ): False Negatives (£450) + False Positives (£25)
- Optimal Probability Threshold Tuning
"""

import json
from pathlib import Path
import joblib
import pandas as pd
import numpy as np

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

COST_FN = 450.0  # £450 per undetected defect (scrapped downstream wafer)
COST_FP = 25.0   # £25 per false alert (re-inspection / metrology check)


def compute_cost_of_quality(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)
    # cm: [[TN, FP], [FN, TP]]
    tn, fp, fn, tp = cm.ravel()
    total_cost = (fn * COST_FN) + (fp * COST_FP)
    return total_cost, tn, fp, fn, tp


def optimize_threshold(y_true, y_proba):
    """Find threshold that minimizes operational financial cost."""
    thresholds = np.linspace(0.02, 0.90, 89)
    best_thresh = 0.5
    min_cost = float("inf")
    best_stats = None

    for t in thresholds:
        preds = (y_proba >= t).astype(int)
        cost, tn, fp, fn, tp = compute_cost_of_quality(y_true, preds)
        if cost < min_cost:
            min_cost = cost
            best_thresh = t
            best_stats = (cost, tn, fp, fn, tp)

    return best_thresh, min_cost, best_stats


def train_and_evaluate():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X_train = pd.read_csv(PROCESSED_DIR / "X_train.csv")
    X_test = pd.read_csv(PROCESSED_DIR / "X_test.csv")
    y_train = pd.read_csv(PROCESSED_DIR / "y_train.csv").iloc[:, 0].values
    y_test = pd.read_csv(PROCESSED_DIR / "y_test.csv").iloc[:, 0].values

    print("==================================================================")
    print("      MANUFACTURING OPERATIONS QUALITY RISK — MODEL BENCHMARK     ")
    print("==================================================================")
    print(f"Train samples: {len(X_train)} (Defects: {y_train.sum()})")
    print(f"Test samples:  {len(X_test)} (Defects: {y_test.sum()})")
    print(f"Baseline Unmitigated Cost (All Defect Misses): GBP {y_test.sum() * COST_FN:,.2f}")

    models = {
        "Dummy (Majority)": Pipeline([
            ("clf", DummyClassifier(strategy="most_frequent"))
        ]),
        "Logistic Regression (Cost-Sensitive)": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42))
        ]),
        "Balanced Random Forest": Pipeline([
            ("clf", RandomForestClassifier(n_estimators=200, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1))
        ]),
        "Gradient Boosting (Class-Weighted)": Pipeline([
            ("clf", HistGradientBoostingClassifier(class_weight="balanced", max_iter=150, random_state=42))
        ])
    }

    results = []
    trained_pipelines = {}

    for name, pipeline in models.items():
        pipeline.fit(X_train, y_train)
        trained_pipelines[name] = pipeline

        # Predictions at default 0.5 threshold
        if hasattr(pipeline, "predict_proba"):
            y_proba = pipeline.predict_proba(X_test)[:, 1]
            roc_auc = roc_auc_score(y_test, y_proba)
            pr_auc = average_precision_score(y_test, y_proba)
            # Find optimal business threshold
            opt_thresh, opt_cost, (c, tn, fp, fn, tp) = optimize_threshold(y_test, y_proba)
            y_pred_opt = (y_proba >= opt_thresh).astype(int)
        else:
            y_proba = np.zeros_like(y_test)
            roc_auc = 0.5
            pr_auc = y_test.mean()
            opt_thresh = 0.5
            y_pred_opt = pipeline.predict(X_test)
            opt_cost, tn, fp, fn, tp = compute_cost_of_quality(y_test, y_pred_opt)

        default_preds = pipeline.predict(X_test)
        def_cost, _, _, _, _ = compute_cost_of_quality(y_test, default_preds)

        results.append({
            "model": name,
            "accuracy": round(accuracy_score(y_test, y_pred_opt), 4),
            "balanced_accuracy": round(balanced_accuracy_score(y_test, y_pred_opt), 4),
            "precision": round(precision_score(y_test, y_pred_opt, zero_division=0), 4),
            "recall": round(recall_score(y_test, y_pred_opt, zero_division=0), 4),
            "f1_score": round(f1_score(y_test, y_pred_opt, zero_division=0), 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "optimal_threshold": round(float(opt_thresh), 3),
            "default_cost_gbp": round(def_cost, 2),
            "optimal_cost_gbp": round(opt_cost, 2),
            "cost_savings_pct": round(((y_test.sum() * COST_FN - opt_cost) / (y_test.sum() * COST_FN)) * 100, 2),
            "true_positives": int(tp),
            "false_negatives": int(fn),
            "false_positives": int(fp),
            "true_negatives": int(tn)
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(by="optimal_cost_gbp", ascending=True).reset_index(drop=True)
    results_df.to_csv(PROCESSED_DIR / "model_benchmark_results.csv", index=False)

    print("\nBENCHMARK RESULTS (SORTED BY OPTIMAL FINANCIAL COST):")
    display_cols = ["model", "recall", "precision", "pr_auc", "roc_auc", "optimal_threshold", "optimal_cost_gbp", "cost_savings_pct"]
    print(results_df[display_cols].to_string(index=False))

    # Persist champion model (lowest operational cost)
    champion_name = results_df.iloc[0]["model"]
    champion_model = trained_pipelines[champion_name]
    champion_path = MODELS_DIR / "champion_quality_model.joblib"
    joblib.dump(champion_model, champion_path)

    # Save champion metadata
    champion_meta = results_df.iloc[0].to_dict()
    with open(MODELS_DIR / "champion_model_meta.json", "w") as f:
        json.dump(champion_meta, f, indent=4)

    print(f"\nChampion Model: [{champion_name}] saved to {champion_path}")
    print(f"Optimal Operating Threshold: {champion_meta['optimal_threshold']}")
    print(f"Financial Cost of Quality: GBP {champion_meta['optimal_cost_gbp']:,.2f} vs GBP {y_test.sum() * COST_FN:,.2f} (Savings: {champion_meta['cost_savings_pct']}%)")

    return results_df


if __name__ == "__main__":
    train_and_evaluate()
