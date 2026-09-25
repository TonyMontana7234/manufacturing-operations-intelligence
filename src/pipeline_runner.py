"""Master Pipeline Orchestrator.

Runs the end-to-end Manufacturing Operations Intelligence workflow:
1. Ingestion (Raw Preservation)
2. Data Quality Profiling
3. PostgreSQL/SQLite Warehouse Population
4. SQL Analytics & Aggregations
5. Chronological Feature Selection
6. Cost-Sensitive ML Model Training
7. SHAP Explainability & Root-Cause Playbooks
8. 14-Day Yield Forecasting
9. Operations Lot Routing & Dynamic Safety Stock
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.ingestion.download_secom import download_secom
from src.quality.generate_quality_report import generate_quality_report
from src.transformation.load_database import main as load_db_main
from src.transformation.run_sql_analytics import run_analytics
from src.modelling.feature_selection import run_feature_pipeline
from src.modelling.train_models import train_and_evaluate
from src.modelling.explainability_shap import run_explainability
from src.forecasting.yield_forecasting import run_yield_forecasting
from src.forecasting.inventory_operations_logic import run_operations_logic


def run_full_pipeline():
    start_time = time.time()
    print("==================================================================")
    print("   MANUFACTURING OPERATIONS INTELLIGENCE — FULL PIPELINE RUN      ")
    print("==================================================================")

    print("\n>>> STAGE 1: INGESTION (REPRODUCIBLE DATA ACQUISITION)")
    download_secom()

    print("\n>>> STAGE 2: DATA PROFILING & AUTOMATED AUDIT")
    generate_quality_report()

    print("\n>>> STAGE 3: DATA WAREHOUSE POPULATION (DIMENSIONAL CORE)")
    load_db_main()

    print("\n>>> STAGE 4: SQL ANALYTICS & AGGREGATIONS")
    run_analytics()

    print("\n>>> STAGE 5: CHRONOLOGICAL FEATURE SELECTION & RANKING")
    run_feature_pipeline()

    print("\n>>> STAGE 6: COST-SENSITIVE MODEL TRAINING & THRESHOLD OPTIMIZATION")
    train_and_evaluate()

    print("\n>>> STAGE 7: EXPLAINABLE AI & ROOT-CAUSE DIAGNOSTICS (SHAP)")
    run_explainability()

    print("\n>>> STAGE 8: 14-DAY YIELD & SCRAP FORECASTING")
    run_yield_forecasting()

    print("\n>>> STAGE 9: OPERATIONAL LOT ROUTING & SAFETY STOCK SIMULATION")
    run_operations_logic()

    elapsed = time.time() - start_time
    print("\n==================================================================")
    print(f"   PIPELINE EXECUTION COMPLETED SUCCESSFULLY IN {elapsed:.2f}s    ")
    print("==================================================================")


if __name__ == "__main__":
    run_full_pipeline()
