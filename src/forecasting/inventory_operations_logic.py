"""Operational Decision Support & Dynamic Inventory Buffering Logic.

Connects ML failure risk predictions to:
1. Dynamic Raw Wafer Starts & Safety Stock Sizing
2. 3-Tier Lot Risk Routing (Hold / Inspect / Release)
3. Automated Real-time Operations Alert Log
"""

from pathlib import Path
import json
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"
DASHBOARDS_DIR = BASE_DIR / "dashboards"

SCRAP_COST_PER_UNIT = 450.0   # GBP
INSPECTION_COST_PER_UNIT = 25.0  # GBP


def run_operations_logic():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading test features and champion model...")
    pipeline = joblib.load(MODELS_DIR / "champion_quality_model.joblib")
    with open(MODELS_DIR / "champion_model_meta.json", "r") as f:
        meta = json.load(f)

    threshold = meta["optimal_threshold"]

    X_test = pd.read_csv(PROCESSED_DIR / "X_test.csv")
    y_test = pd.read_csv(PROCESSED_DIR / "y_test.csv").iloc[:, 0].values

    # Predict risk probabilities
    risk_probabilities = pipeline.predict_proba(X_test)[:, 1]

    # Assign 3-Tier Action Routing
    def assign_routing(prob):
        if prob >= threshold:
            return "TIER_1_CRITICAL", "HOLD: Route to Inline Metrology & Defect Review Station", "URGENT"
        elif prob >= 0.08:
            return "TIER_2_ELEVATED", "MONITOR: Tool chamber drift detected; schedule preventative clean", "MEDIUM"
        else:
            return "TIER_3_NOMINAL", "RELEASE: Nominal lot quality; fast-track to CMP / metallization", "LOW"

    routing_data = [assign_routing(p) for p in risk_probabilities]
    tier_codes = [r[0] for r in routing_data]
    action_plans = [r[1] for r in routing_data]
    urgencies = [r[2] for r in routing_data]

    lot_alerts_df = pd.DataFrame({
        "lot_id": [f"LOT_{i:04d}" for i in range(1, len(risk_probabilities) + 1)],
        "failure_risk_pct": np.round(risk_probabilities * 100, 2),
        "risk_tier": tier_codes,
        "operational_action": action_plans,
        "alert_urgency": urgencies,
        "actual_quality": np.where(y_test == 1, "DEFECT", "CONFORMING")
    })

    lot_alerts_df.to_csv(PROCESSED_DIR / "operational_alerts.csv", index=False)

    print("==================================================================")
    print("        OPERATIONAL DECISION SUPPORT — LOT ROUTING ALERTS         ")
    print("==================================================================")
    tier_summary = lot_alerts_df["risk_tier"].value_counts()
    for tier, count in tier_summary.items():
        print(f"  {tier:18s}: {count:4d} lots ({count/len(lot_alerts_df):.1%})")

    # Safety Stock Simulation
    target_delivery = 1000  # 1,000 finished wafers required per month
    service_level_z = 2.05  # 98% service level
    base_yield = 0.9336     # Baseline 93.36% yield (6.64% defect rate)
    yield_std = 0.025       # Historical std dev in daily yield

    lead_time_days = 21     # 3-week semiconductor fab cycle time

    planned_starts = int(np.ceil(target_delivery / base_yield))
    safety_buffer = int(np.ceil(service_level_z * np.sqrt(lead_time_days) * (target_delivery * yield_std)))
    total_inventory_order = planned_starts + safety_buffer

    safety_stock_df = pd.DataFrame([{
        "monthly_target_wafers": target_delivery,
        "service_level_target": "98.0%",
        "base_yield_rate_pct": f"{base_yield*100:.2f}%",
        "planned_wafer_starts": planned_starts,
        "dynamic_safety_buffer": safety_buffer,
        "total_material_order": total_inventory_order,
        "cost_of_buffer_gbp": round(safety_buffer * 120.0, 2)  # Raw silicon wafer substrate £120
    }])
    safety_stock_df.to_csv(PROCESSED_DIR / "safety_stock_simulation.csv", index=False)

    print("\nDYNAMIC SAFETY STOCK SIMULATION (MONTHLY PLANNING):")
    print(safety_stock_df.to_string(index=False))

    # Save visual plot of alert distribution
    plt.figure(figsize=(9, 4.5))
    colors = ["#e74c3c", "#f39c12", "#2ecc71"]
    order = ["TIER_1_CRITICAL", "TIER_2_ELEVATED", "TIER_3_NOMINAL"]
    sns.countplot(data=lot_alerts_df, x="risk_tier", hue="risk_tier", order=order, palette=colors, legend=False)
    plt.title("Operational Lot Dispatch: Real-Time Risk Routing Distribution", fontsize=12, fontweight="bold", pad=12)
    plt.xlabel("Operational Action Tier")
    plt.ylabel("Lots Monitored")
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.tight_layout()

    plot_path = DASHBOARDS_DIR / "operational_alerts_summary.png"
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"\nSaved operations alert plot to {plot_path}")

    return lot_alerts_df, safety_stock_df


if __name__ == "__main__":
    run_operations_logic()
