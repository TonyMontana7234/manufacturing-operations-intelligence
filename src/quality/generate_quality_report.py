import json
from pathlib import Path
import pandas as pd
import numpy as np

RAW_DIR = Path("data/raw")
QUALITY_DIR = Path("data/quality")


def generate_quality_report():
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)

    features = pd.read_csv(RAW_DIR / "secom_features_raw.csv")
    labels = pd.read_csv(RAW_DIR / "secom_labels_raw.csv")

    n_rows, n_cols = features.shape
    duplicate_rows = int(features.duplicated().sum())

    # Timestamp handling
    has_ts = "timestamp" in features.columns
    if has_ts:
        ts_series = pd.to_datetime(features["timestamp"], format="mixed", dayfirst=True)
        ts_min = str(ts_series.min())
        ts_max = str(ts_series.max())
        sensor_df = features.drop(columns=["timestamp"])
    else:
        ts_min, ts_max = None, None
        sensor_df = features

    total_cells = int(sensor_df.size)
    total_missing = int(sensor_df.isna().sum().sum())
    missing_rate = (total_missing / total_cells) * 100

    # Column missingness breakdown
    missing_per_col = sensor_df.isna().sum()
    missing_pct_per_col = (missing_per_col / n_rows) * 100

    cols_gt_50 = missing_pct_per_col[missing_pct_per_col > 50].sort_values(ascending=False)
    cols_gt_50_df = pd.DataFrame({
        "column": cols_gt_50.index,
        "missing_count": missing_per_col[cols_gt_50.index].values,
        "missing_pct": cols_gt_50.values.round(2)
    })
    cols_gt_50_df.to_csv(QUALITY_DIR / "high_missing_columns.csv", index=False)

    # Constant / zero-variance columns (nunique <= 1)
    nunique_per_col = sensor_df.nunique(dropna=True)
    constant_cols = nunique_per_col[nunique_per_col <= 1].index.tolist()
    const_df = pd.DataFrame({"column": constant_cols, "unique_values": [nunique_per_col[c] for c in constant_cols]})
    const_df.to_csv(QUALITY_DIR / "constant_columns.csv", index=False)

    # Label distribution
    target_series = labels.iloc[:, 0]
    label_counts = target_series.value_counts().to_dict()
    pass_obs = int(label_counts.get(-1, 0))
    fail_obs = int(label_counts.get(1, 0))

    # Overall health determination
    quality_status = "WARNING" if (len(cols_gt_50) > 0 or len(constant_cols) > 0 or fail_obs / n_rows < 0.1) else "PASS"

    # Detailed column profiling
    profile_records = []
    for col in sensor_df.columns:
        s = sensor_df[col]
        profile_records.append({
            "column": col,
            "dtype": str(s.dtype),
            "missing_count": int(s.isna().sum()),
            "missing_pct": round(float(s.isna().mean() * 100), 2),
            "unique_count": int(s.nunique(dropna=True)),
            "is_constant": bool(s.nunique(dropna=True) <= 1),
            "mean": round(float(s.mean()), 4) if pd.notna(s.mean()) else None,
            "std": round(float(s.std()), 4) if pd.notna(s.std()) else None,
            "min": round(float(s.min()), 4) if pd.notna(s.min()) else None,
            "max": round(float(s.max()), 4) if pd.notna(s.max()) else None
        })
    pd.DataFrame(profile_records).to_csv(QUALITY_DIR / "column_profiles.csv", index=False)

    summary = {
        "dataset": "SECOM",
        "rows": n_rows,
        "features": n_cols,
        "duplicate_rows": duplicate_rows,
        "missing_value_rate_pct": round(missing_rate, 2),
        "columns_gt_50_pct_missing": len(cols_gt_50),
        "constant_columns": len(constant_cols),
        "pass_observations": pass_obs,
        "fail_observations": fail_obs,
        "failure_rate_pct": round((fail_obs / n_rows) * 100, 2),
        "timestamp_start": ts_min,
        "timestamp_end": ts_max,
        "quality_status": quality_status
    }

    with open(QUALITY_DIR / "data_quality_summary.json", "w") as f:
        json.dump(summary, f, indent=4)

    report_text = f"""DATA QUALITY REPORT
===================

Dataset: SECOM

Rows: {n_rows:,}
Features: {n_cols:,}

Duplicate rows: {duplicate_rows}

Missing-value rate: {missing_rate:.2f}%

Columns >50% missing: {len(cols_gt_50)}

Constant columns: {len(constant_cols)}

Pass observations: {pass_obs:,}
Fail observations: {fail_obs}

Quality status: {quality_status}
"""
    with open(QUALITY_DIR / "data_quality_report.txt", "w") as f:
        f.write(report_text)

    print(report_text)
    return summary


if __name__ == "__main__":
    generate_quality_report()
