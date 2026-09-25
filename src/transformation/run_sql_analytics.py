"""Execute and export SQL Operational Analytics queries."""

import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "manufacturing_ops.db"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def run_analytics():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    print("==================================================================")
    print("      MANUFACTURING OPERATIONS INTELLIGENCE — SQL ANALYTICS       ")
    print("==================================================================")

    # 1. Shift Performance
    q_shift = """
        SELECT 
            p.shift_code,
            COUNT(p.production_id) AS total_runs,
            SUM(q.is_defect) AS defective_units,
            ROUND((CAST(SUM(q.is_defect) AS FLOAT) / COUNT(p.production_id)) * 100, 2) AS defect_rate_pct,
            ROUND((CAST(COUNT(p.production_id) - SUM(q.is_defect) AS FLOAT) / COUNT(p.production_id)) * 100, 2) AS yield_rate_pct,
            SUM(q.estimated_scrap_cost) AS total_scrap_cost_gbp
        FROM dim_production_entity p
        JOIN fact_quality_outcome q ON p.production_id = q.production_id
        GROUP BY p.shift_code
        ORDER BY defect_rate_pct DESC;
    """
    df_shift = pd.read_sql_query(q_shift, conn)
    df_shift.to_csv(PROCESSED_DIR / "analytics_shift_performance.csv", index=False)
    print("\n[1] OPERATIONAL SHIFT PERFORMANCE")
    print(df_shift.to_string(index=False))

    # 2. Weekly Scrap Exposure
    q_weekly = """
        SELECT 
            p.week_of_year,
            MIN(p.run_date) AS week_start,
            COUNT(p.production_id) AS total_wafers,
            SUM(q.is_defect) AS scrap_wafers,
            ROUND((CAST(SUM(q.is_defect) AS FLOAT) / COUNT(p.production_id)) * 100, 2) AS weekly_defect_rate_pct,
            SUM(q.estimated_scrap_cost) AS weekly_scrap_cost_gbp
        FROM dim_production_entity p
        JOIN fact_quality_outcome q ON p.production_id = q.production_id
        GROUP BY p.week_of_year
        ORDER BY p.week_of_year ASC;
    """
    df_weekly = pd.read_sql_query(q_weekly, conn)
    df_weekly.to_csv(PROCESSED_DIR / "analytics_weekly_scrap.csv", index=False)
    print("\n[2] WEEKLY PRODUCTION & SCRAP EXPOSURE (FIRST 5 WEEKS)")
    print(df_weekly.head(5).to_string(index=False))

    # 3. Day of Week Analysis
    q_dow = """
        SELECT 
            p.day_name,
            COUNT(p.production_id) AS total_wafers,
            SUM(q.is_defect) AS defect_count,
            ROUND((CAST(SUM(q.is_defect) AS FLOAT) / COUNT(p.production_id)) * 100, 2) AS defect_rate_pct
        FROM dim_production_entity p
        JOIN fact_quality_outcome q ON p.production_id = q.production_id
        GROUP BY p.day_name
        ORDER BY defect_rate_pct DESC;
    """
    df_dow = pd.read_sql_query(q_dow, conn)
    df_dow.to_csv(PROCESSED_DIR / "analytics_day_of_week.csv", index=False)
    print("\n[3] DAY-OF-WEEK QUALITY VARIANCE")
    print(df_dow.to_string(index=False))

    # 4. Sensor Governance
    q_sensor = """
        SELECT 
            COUNT(*) AS total_instrumentation_sensors,
            SUM(is_constant) AS constant_zero_variance,
            SUM(CASE WHEN missing_rate_pct > 50.0 THEN 1 ELSE 0 END) AS severe_missing_gt_50pct,
            SUM(is_quarantined) AS total_quarantined,
            SUM(CASE WHEN is_quarantined = 0 THEN 1 ELSE 0 END) AS vetted_ml_features
        FROM dim_sensor;
    """
    df_sensor = pd.read_sql_query(q_sensor, conn)
    df_sensor.to_csv(PROCESSED_DIR / "analytics_sensor_governance.csv", index=False)
    print("\n[4] SENSOR GOVERNANCE & DATA AUDIT")
    print(df_sensor.to_string(index=False))

    conn.close()
    print("\nAnalytics export complete. Saved reports to data/processed/")


if __name__ == "__main__":
    run_analytics()
