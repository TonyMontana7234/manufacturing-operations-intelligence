# Technical Architecture Specification
## Manufacturing Operations Intelligence Platform

---

## 1. System Architecture Diagram

```mermaid
flowchart TD
    subgraph INGESTION["1. Ingestion Layer"]
        A1["Fab Equipment Sensors\n(590 Continuous Features)"] --> A2["Python Ingestion Service\n(download_secom.py)"]
        A2 --> A3[("data/raw/\nsecom_features_raw.csv\nsecom_labels_raw.csv")]
    end

    subgraph QUALITY["2. Data Quality & Governance Layer"]
        A3 --> B1["Data Profiler Engine\n(generate_quality_report.py)"]
        B1 --> B2["Health Status: WARNING\n• 4.54% Missingness\n• 116 Constant Cols\n• 28 Cols >50% Missing"]
        B2 --> B3[("data/quality/\ncolumn_profiles.csv\nhigh_missing_columns.csv\nconstant_columns.csv")]
    end

    subgraph WAREHOUSE["3. Enterprise Warehouse (PostgreSQL)"]
        B3 --> C1["staging.secom_raw\n(Relational Keys + JSONB Sensor Data)"]
        C1 --> C2["core.dim_production_entity\n(Run Date, Shift, Week Hierarchy)"]
        C1 --> C3["core.dim_sensor\n(Governance & Quarantine Flags)"]
        C1 --> C4["core.fact_quality_outcome\n(Conforming vs Defective, Scrap Cost)"]
        C2 & C3 & C4 --> C5["analytics.v_production_yield_daily\nanalytics.v_shift_performance\nanalytics.v_sensor_governance_summary"]
    end

    subgraph ANALYTICS_ENGINE["4. Advanced Analytics & ML Core"]
        C5 --> D1["Chronological Split & Feature Selection\n(Top-50 Sensors, 80/20 Chrono Split)"]
        D1 --> D2["Cost-Sensitive Classifier\n(Threshold Tuning: 0.14)\n• 88.24% Defect Recall\n• 34.97% CoQ Savings"]
        D2 --> D3["Explainable AI (SHAP)\n(Attribute 578, 429, 65...)"]
        D1 --> D4["14-Day Yield Forecaster\n(Rolling Lag & Volatility Regressor)"]
    end

    subgraph CONSUMPTION["5. Operational Decision Support & BI"]
        D2 & D3 --> E1["Lot Dispatch Queue\n(data/processed/operational_alerts.csv)"]
        D4 --> E2["Dynamic Safety Stock Planning\n(data/processed/safety_stock_simulation.csv)"]
        C5 & D2 & D3 & D4 --> E3["Power BI Semantic Model\n(4-Page Executive & Engineering Cockpit)"]
    end
```

---

## 2. Component Design & Responsibilities

### Tier 1 — Data Ingestion & Preservation
* **Module:** [download_secom.py](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/src/ingestion/download_secom.py)
* **Contract:** Fetches verified dataset from UCI Repository (ID: 179). Never overwrites or mutates raw artifacts in `data/raw/`.

### Tier 2 — Data Quality Gate
* **Module:** [generate_quality_report.py](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/src/quality/generate_quality_report.py)
* **Contract:** Evaluates nullity, variance, and cardinality before promotion to relational core. Generates deterministic quarantine registers for unstable instrumentation.

### Tier 3 — Relational & Medallion Warehouse
* **Modules:** [01_init_database.sql](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/sql/01_init_database.sql), [02_staging_schema.sql](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/sql/02_staging_schema.sql), [03_core_schema.sql](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/sql/03_core_schema.sql), [04_analytics_views.sql](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/sql/04_analytics_views.sql)
* **Contract:** Implements a 3-tier architecture: Staging (JSONB), Core (Dimensional), and Analytics (KPI Views).

### Tier 4 — Machine Learning & Explainability
* **Modules:** [feature_selection.py](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/src/modelling/feature_selection.py), [train_models.py](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/src/modelling/train_models.py), [explainability_shap.py](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/src/modelling/explainability_shap.py)
* **Contract:** Prevents temporal leakage via chronological splitting. Tunes thresholds against financial Cost-of-Quality (CoQ). Provides SHAP root-cause attributions for physical chamber maintenance.

### Tier 5 — Operations & BI Cockpit
* **Modules:** [yield_forecasting.py](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/src/forecasting/yield_forecasting.py), [inventory_operations_logic.py](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/src/forecasting/inventory_operations_logic.py), [power_bi_data_model_spec.md](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/dashboards/power_bi_data_model_spec.md)
* **Contract:** Exposes real-time lot hold/release dispatch queues and dynamic material safety stock buffers for plant leadership.
