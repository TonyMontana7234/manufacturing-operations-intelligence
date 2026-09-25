"""Feature Selection & Chronological Train/Test Partitioning Pipeline.

Implements:
1. Removal of zero-variance and high-missingness features
2. Chronological Train/Test Split (prevents time-travel data leakage)
3. Train-only Median Imputation
4. Robust Feature Ranking via Mutual Information & Random Forest Importance
5. Top-K Feature Selection to prevent overfitting
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import mutual_info_classif
from sklearn.ensemble import RandomForestClassifier

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
QUALITY_DIR = BASE_DIR / "data" / "quality"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def run_feature_pipeline(train_ratio: float = 0.8, top_k: int = 50):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    features = pd.read_csv(RAW_DIR / "secom_features_raw.csv")
    labels = pd.read_csv(RAW_DIR / "secom_labels_raw.csv")

    # Target: 1 for defect, 0 for pass (convert from -1/1)
    y = (labels.iloc[:, 0] == 1).astype(int)

    # Sort strictly chronologically by timestamp
    timestamps = pd.to_datetime(features["timestamp"], format="mixed", dayfirst=True)
    sort_idx = timestamps.argsort()
    features = features.iloc[sort_idx].reset_index(drop=True)
    y = y.iloc[sort_idx].reset_index(drop=True)

    sensor_df = features.drop(columns=["timestamp"])

    # Load quarantined columns from quality layer
    with open(QUALITY_DIR / "data_quality_summary.json", "r") as f:
        q_summary = json.load(f)

    const_df = pd.read_csv(QUALITY_DIR / "constant_columns.csv")
    high_missing_df = pd.read_csv(QUALITY_DIR / "high_missing_columns.csv")

    quarantine_cols = set(const_df["column"]).union(set(high_missing_df["column"]))
    candidate_cols = [c for c in sensor_df.columns if c not in quarantine_cols]

    print(f"Total Raw Sensors:          {sensor_df.shape[1]}")
    print(f"Quarantined Sensors:        {len(quarantine_cols)} (116 constant + 28 >50% missing)")
    print(f"Candidate Sensors for ML:   {len(candidate_cols)}")

    X_candidates = sensor_df[candidate_cols]

    # Chronological Split
    n_total = len(X_candidates)
    n_train = int(n_total * train_ratio)

    X_train_raw = X_candidates.iloc[:n_train].copy()
    X_test_raw = X_candidates.iloc[n_train:].copy()
    y_train = y.iloc[:n_train].copy()
    y_test = y.iloc[n_train:].copy()

    print(f"\nChronological Split (Train {train_ratio*100:.0f}% / Test {(1-train_ratio)*100:.0f}%):")
    print(f"  Training Set:   {X_train_raw.shape[0]} runs ({y_train.sum()} defects, {y_train.mean():.2%} defect rate)")
    print(f"  Test Set:       {X_test_raw.shape[0]} runs ({y_test.sum()} defects, {y_test.mean():.2%} defect rate)")

    # Train-only Imputation
    imputer = SimpleImputer(strategy="median")
    X_train_imp = pd.DataFrame(
        imputer.fit_transform(X_train_raw),
        columns=candidate_cols
    )
    X_test_imp = pd.DataFrame(
        imputer.transform(X_test_raw),
        columns=candidate_cols
    )

    # Feature Importance via Random Forest (Cost-balanced)
    print("\nComputing Feature Importance via Random Forest & Mutual Information...")
    rf = RandomForestClassifier(
        n_estimators=100,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train_imp, y_train)
    rf_importance = rf.feature_importances_

    # Mutual Information
    mi = mutual_info_classif(X_train_imp, y_train, random_state=42)

    # Composite Ranking Score
    ranking_df = pd.DataFrame({
        "sensor_code": candidate_cols,
        "rf_importance": rf_importance,
        "mutual_info": mi
    })
    # Normalize and create blended score
    rf_norm = ranking_df["rf_importance"] / ranking_df["rf_importance"].max()
    mi_norm = ranking_df["mutual_info"] / (ranking_df["mutual_info"].max() if ranking_df["mutual_info"].max() > 0 else 1)
    ranking_df["composite_score"] = (0.7 * rf_norm) + (0.3 * mi_norm)
    ranking_df = ranking_df.sort_values(by="composite_score", ascending=False).reset_index(drop=True)

    ranking_df.to_csv(QUALITY_DIR / "feature_importance_ranking.csv", index=False)

    top_features = ranking_df.head(top_k)["sensor_code"].tolist()
    print(f"\nSelected Top {top_k} Features based on composite ranking.")
    print("Top 10 Sensors:", top_features[:10])

    # Filter to selected Top-K
    X_train_selected = X_train_imp[top_features]
    X_test_selected = X_test_imp[top_features]

    # Save artifacts
    X_train_selected.to_csv(PROCESSED_DIR / "X_train.csv", index=False)
    X_test_selected.to_csv(PROCESSED_DIR / "X_test.csv", index=False)
    y_train.to_csv(PROCESSED_DIR / "y_train.csv", index=False)
    y_test.to_csv(PROCESSED_DIR / "y_test.csv", index=False)

    with open(PROCESSED_DIR / "selected_features.json", "w") as f:
        json.dump({
            "top_k": top_k,
            "train_samples": len(X_train_selected),
            "test_samples": len(X_test_selected),
            "features": top_features
        }, f, indent=4)

    print("\nFeature selection complete! Saved training matrices to data/processed/")
    return X_train_selected, X_test_selected, y_train, y_test


if __name__ == "__main__":
    run_feature_pipeline()
