"""ETL Loader for Manufacturing Operations Intelligence Platform.

Populates Staging, Core, and Analytics layers from raw SECOM CSVs and data quality profiling.
Supports PostgreSQL (default target) as well as SQLite local fallback.
"""

import argparse
import json
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
QUALITY_DIR = BASE_DIR / "data" / "quality"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def assign_shift(hour: int) -> str:
    """Classify 24-hour timestamp into manufacturing factory shift."""
    if 6 <= hour < 14:
        return "DAY_SHIFT"
    elif 14 <= hour < 22:
        return "EVENING_SHIFT"
    else:
        return "NIGHT_SHIFT"


def build_pipeline_data():
    """Extract and transform raw datasets into dimensional tables."""
    features = pd.read_csv(RAW_DIR / "secom_features_raw.csv")
    labels = pd.read_csv(RAW_DIR / "secom_labels_raw.csv")

    with open(QUALITY_DIR / "data_quality_summary.json", "r") as f:
        quality_summary = json.load(f)

    column_profiles = pd.read_csv(QUALITY_DIR / "column_profiles.csv")

    # 1. Parse timestamps
    timestamps = pd.to_datetime(features["timestamp"], format="mixed", dayfirst=True)
    sensor_df = features.drop(columns=["timestamp"])

    # 2. Build core.dim_production_entity
    dim_production = pd.DataFrame({
        "production_id": np.arange(1, len(features) + 1),
        "run_timestamp": timestamps,
        "run_date": timestamps.dt.date,
        "run_hour": timestamps.dt.hour,
        "shift_code": [assign_shift(h) for h in timestamps.dt.hour],
        "day_name": timestamps.dt.day_name(),
        "week_of_year": timestamps.dt.isocalendar().week.astype(int),
        "month_name": timestamps.dt.month_name()
    })

    # 3. Build core.fact_quality_outcome
    raw_labels = labels.iloc[:, 0].astype(int)
    is_defects = raw_labels == 1
    # Modeling cost: scrap cost of £450 per defect wafer
    fact_quality = pd.DataFrame({
        "production_id": np.arange(1, len(features) + 1),
        "raw_label": raw_labels,
        "is_defect": is_defects,
        "defect_classification": np.where(is_defects, "NON_CONFORMING", "CONFORMING"),
        "estimated_scrap_cost": np.where(is_defects, 450.00, 0.00),
        "reinspection_flag": is_defects
    })

    # 4. Build core.dim_sensor
    dim_sensor = pd.DataFrame({
        "sensor_id": np.arange(1, len(column_profiles) + 1),
        "sensor_code": column_profiles["column"],
        "sensor_alias": [f"sensor_{i:03d}" for i in range(1, len(column_profiles) + 1)],
        "category": "INSPECTION_METRIC",
        "is_constant": column_profiles["is_constant"],
        "missing_rate_pct": column_profiles["missing_pct"],
        "is_quarantined": (column_profiles["missing_pct"] > 50.0) | column_profiles["is_constant"],
        "quarantine_reason": np.where(
            column_profiles["missing_pct"] > 50.0,
            "HIGH_MISSING_RATE_GT_50_PCT",
            np.where(column_profiles["is_constant"], "ZERO_VARIANCE_CONSTANT_FEATURE", "NONE")
        ),
        "mean_val": column_profiles["mean"],
        "std_val": column_profiles["std"],
        "min_val": column_profiles["min"],
        "max_val": column_profiles["max"]
    })

    # 5. Staging records (for relational/JSONB loading)
    staging_records = []
    for idx, row in features.iterrows():
        prod_id = idx + 1
        ts_val = str(timestamps.iloc[idx])
        lbl = int(raw_labels.iloc[idx])
        # Convert row sensor metrics to dict, dropping timestamp
        s_data = row.drop(labels=["timestamp"]).dropna().to_dict()
        staging_records.append({
            "production_id": prod_id,
            "event_timestamp": ts_val,
            "quality_label": lbl,
            "sensor_data_json": json.dumps(s_data)
        })
    staging_df = pd.DataFrame(staging_records)

    return dim_production, fact_quality, dim_sensor, staging_df, quality_summary


def load_to_sqlite(db_path: Path):
    """Load dimensional entities into a local SQLite database for offline analysis."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")

    dim_production, fact_quality, dim_sensor, staging_df, quality_summary = build_pipeline_data()

    print(f"Loading data into SQLite warehouse: {db_path}...")
    dim_production.to_sql("dim_production_entity", engine, if_exists="replace", index=False)
    fact_quality.to_sql("fact_quality_outcome", engine, if_exists="replace", index=False)
    dim_sensor.to_sql("dim_sensor", engine, if_exists="replace", index=False)
    staging_df.to_sql("staging_secom_raw", engine, if_exists="replace", index=False)

    # Save summary log
    audit_df = pd.DataFrame([{
        "batch_run_id": "INIT_BATCH_001",
        "dataset_name": quality_summary["dataset"],
        "total_records": quality_summary["rows"],
        "total_features": quality_summary["features"],
        "duplicate_rows": quality_summary["duplicate_rows"],
        "overall_missing_pct": quality_summary["missing_value_rate_pct"],
        "high_missing_cols_count": quality_summary["columns_gt_50_pct_missing"],
        "constant_cols_count": quality_summary["constant_columns"],
        "pass_count": quality_summary["pass_observations"],
        "fail_count": quality_summary["fail_observations"],
        "quality_status": quality_summary["quality_status"]
    }])
    audit_df.to_sql("data_quality_audit_log", engine, if_exists="replace", index=False)

    print("Successfully populated dimensional tables in local warehouse.")


def main():
    parser = argparse.ArgumentParser(description="Load SECOM data into Database Warehouse")
    parser.add_argument("--db-url", type=str, default=None, help="SQLAlchemy connection URI (e.g. postgresql://user:pass@localhost:5432/manufacturing_ops)")
    args = parser.parse_args()

    if args.db_url:
        print(f"Connecting to database: {args.db_url.split('@')[-1] if '@' in args.db_url else args.db_url}")
        engine = create_engine(args.db_url)
        dim_production, fact_quality, dim_sensor, staging_df, quality_summary = build_pipeline_data()
        
        # Load tables
        dim_production.to_sql("dim_production_entity", engine, schema="core", if_exists="replace", index=False)
        fact_quality.to_sql("fact_quality_outcome", engine, schema="core", if_exists="replace", index=False)
        dim_sensor.to_sql("dim_sensor", engine, schema="core", if_exists="replace", index=False)
        staging_df.to_sql("secom_raw", engine, schema="staging", if_exists="replace", index=False)
        print("Loaded tables into PostgreSQL schema!")
    else:
        # Default local warehouse
        db_file = PROCESSED_DIR / "manufacturing_ops.db"
        load_to_sqlite(db_file)


if __name__ == "__main__":
    main()
