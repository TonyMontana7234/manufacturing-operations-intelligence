"""Operational Yield & Scrap Volume Time-Series Forecasting.

Aggregates daily factory telemetry, creates rolling window and lag features,
and trains a rolling-origin time-series model to forecast future 14-day scrap risk.
"""

from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DASHBOARDS_DIR = BASE_DIR / "dashboards"


def run_yield_forecasting(forecast_horizon_days: int = 14):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)

    # Load daily production aggregate from SQL analytics
    daily_df = pd.read_csv(PROCESSED_DIR / "analytics_weekly_scrap.csv")
    
    # Also load the entity and quality tables to build daily resolution
    import sqlite3
    conn = sqlite3.connect(PROCESSED_DIR / "manufacturing_ops.db")
    q_daily = """
        SELECT 
            p.run_date,
            COUNT(p.production_id) AS total_runs,
            SUM(q.is_defect) AS defect_runs,
            ROUND((CAST(COUNT(p.production_id) - SUM(q.is_defect) AS FLOAT) / COUNT(p.production_id)) * 100, 2) AS yield_rate_pct,
            SUM(q.estimated_scrap_cost) AS total_scrap_cost_gbp
        FROM dim_production_entity p
        JOIN fact_quality_outcome q ON p.production_id = q.production_id
        GROUP BY p.run_date
        ORDER BY p.run_date ASC;
    """
    ts_df = pd.read_sql_query(q_daily, conn)
    conn.close()

    ts_df["run_date"] = pd.to_datetime(ts_df["run_date"])
    ts_df = ts_df.set_index("run_date").asfreq("D", fill_value=0)
    
    # Calculate rolling features
    ts_df["defect_runs_lag1"] = ts_df["defect_runs"].shift(1).fillna(0)
    ts_df["defect_runs_lag7"] = ts_df["defect_runs"].shift(7).fillna(0)
    ts_df["defect_runs_roll7_mean"] = ts_df["defect_runs"].rolling(7, min_periods=1).mean()
    ts_df["defect_runs_roll7_std"] = ts_df["defect_runs"].rolling(7, min_periods=1).std().fillna(0)
    ts_df["day_of_week"] = ts_df.index.dayofweek

    feature_cols = ["defect_runs_lag1", "defect_runs_lag7", "defect_runs_roll7_mean", "defect_runs_roll7_std", "day_of_week"]
    target_col = "defect_runs"

    # Train-test split by time (last 14 days as validation holdout)
    n_days = len(ts_df)
    train_df = ts_df.iloc[:-forecast_horizon_days]
    test_df = ts_df.iloc[-forecast_horizon_days:]

    model = HistGradientBoostingRegressor(max_iter=100, random_state=42)
    model.fit(train_df[feature_cols], train_df[target_col])

    test_preds = model.predict(test_df[feature_cols])
    test_preds = np.clip(test_preds, 0, None)  # Defect count cannot be negative

    mae = mean_absolute_error(test_df[target_col], test_preds)
    rmse = root_mean_squared_error(test_df[target_col], test_preds)

    print("==================================================================")
    print("      OPERATIONAL TIME-SERIES FORECASTING — 14-DAY HORIZON        ")
    print("==================================================================")
    print(f"Total Operating Days Analyzed: {n_days}")
    print(f"Historical Calibration Window: {len(train_df)} days")
    print(f"Holdout Validation Horizon:    {len(test_df)} days")
    print(f"Defect Count MAE:              {mae:.2f} defects/day")
    print(f"Defect Count RMSE:             {rmse:.2f} defects/day")

    # Future projection
    forecast_df = pd.DataFrame({
        "forecast_date": test_df.index.strftime("%Y-%m-%d"),
        "actual_defects": test_df[target_col].values,
        "predicted_defects": np.round(test_preds, 1),
        "predicted_scrap_exposure_gbp": np.round(test_preds * 450.0, 2)
    })
    forecast_df.to_csv(PROCESSED_DIR / "yield_forecast_14d.csv", index=False)

    print("\n14-DAY OPERATIONAL FORECAST SUMMARY:")
    print(forecast_df.head(7).to_string(index=False))

    # Save visual plot
    plt.figure(figsize=(11, 5))
    plt.plot(train_df.index, train_df[target_col], label="Historical Actual Defects", color="#34495e", lw=1.5)
    plt.plot(test_df.index, test_df[target_col], label="Holdout Actual Defects", color="#2980b9", lw=2, marker="o")
    plt.plot(test_df.index, test_preds, label="ML Forecast (14-Day Horizon)", color="#e74c3c", lw=2, linestyle="--", marker="s")
    plt.title("Manufacturing Quality Excursions: 14-Day Predictive Forecast", fontsize=12, fontweight="bold", pad=12)
    plt.xlabel("Operating Date")
    plt.ylabel("Daily Defective Lot Count")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()

    plot_file = DASHBOARDS_DIR / "yield_forecast_14d.png"
    plt.savefig(plot_file, dpi=300)
    plt.close()
    print(f"\nSaved forecast visualization to {plot_file}")

    return forecast_df


if __name__ == "__main__":
    run_yield_forecasting()
