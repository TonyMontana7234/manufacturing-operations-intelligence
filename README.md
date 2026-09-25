# Manufacturing Operations Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.4%2B-orange.svg)](https://scikit-learn.org/)
[![SHAP](https://img.shields.io/badge/SHAP-XAI-brightgreen.svg)](https://github.com/shap/shap)
[![Architecture](https://img.shields.io/badge/Architecture-3--Tier%20Medallion-purple.svg)](#-3-tier-postgresql-data-architecture)

An end-to-end industrial data engineering and operational intelligence platform designed around semiconductor manufacturing telemetry (SECOM). Converts high-dimensional physical sensor streams into automated data quality gates, an enterprise dimensional data warehouse (PostgreSQL), cost-sensitive machine learning failure-risk models, explainable root-cause diagnostics (SHAP), and real-time operational decision support.

---

## 🏭 Industrial Problem & Business Case

In semiconductor fabrication plants (fabs), silicon wafers undergo hundreds of chemical, photolithographic, and thermal steps. Even microscopic chamber shifts or gas flow drift can result in defective wafers.

* **The Problem:** Traditional fabs detect defects at End-of-Line (EOL) electrical probe—after 100% of manufacturing, chemical, and energy costs have already been sunk.
* **The Financial Asymmetry:**
  * **Cost of False Negative ($C_{FN}$):** An undetected defective wafer reaches downstream packaging/assembly, wasting **£450 per unit**.
  * **Cost of False Positive ($C_{FP}$):** A conforming wafer flagged for secondary inline metrology re-testing costs **£25 per unit**.
* **The Solution:** An integrated operations intelligence platform that predicts quality failure risk in-situ, prescribes root causes to technicians, and automates shop-floor lot routing (Hold/Inspect/Release).

---

## 🏗️ 3-Tier PostgreSQL Data Architecture

To prevent unwieldy 590-column wide-table anti-patterns, the system implements a **hybrid relational + JSONB dimensional model**:

```text
                    PostgreSQL Warehouse (manufacturing_ops)
                                      │
        ┌─────────────────────────────┴─────────────────────────────┐
        ▼                                                           ▼
   [ STAGING ]                                                 [ CORE ]
  staging.secom_raw                                        core.dim_production_entity
  (Relational Keys + JSONB Sensor Payload)                 (Run Date, Shift, Week Hierarchy)
  staging.data_quality_audit_log                                    │
  (Automated Ingestion Quality Health Log)                 core.dim_sensor
                                                           (Quarantine & Calibration Catalog)
                                                                    │
                                                           core.fact_quality_outcome
                                                           (Defect Conformance & Scrap Costs)
                                                                    │
                                                                    ▼
                                                              [ ANALYTICS ]
                                                           analytics.v_production_yield_daily
                                                           analytics.v_shift_performance
                                                           analytics.v_sensor_governance_summary
```

### Schemas & DDL Modules
* **[01_init_database.sql](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/sql/01_init_database.sql):** Database and schema initializations.
* **[02_staging_schema.sql](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/sql/02_staging_schema.sql):** Staging tables with JSONB GIN indexing for raw telemetry.
* **[03_core_schema.sql](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/sql/03_core_schema.sql):** Normalized star schema (`dim_production_entity`, `dim_sensor`, `fact_quality_outcome`).
* **[04_analytics_views.sql](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/sql/04_analytics_views.sql):** Executive yield KPIs and sensor governance reporting.
* **[05_analytical_queries.sql](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/sql/05_analytical_queries.sql):** Shift variance and weekly scrap risk queries.

---

## 📊 Data Quality & Profiling Scorecard

Automated profiling executed on the raw UCI SECOM dataset (ID: 179) via [generate_quality_report.py](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/src/quality/generate_quality_report.py):

| Metric | Result | Operational Status |
|:---|:---|:---|
| **Total Production Runs** | 1,567 observations | Verified |
| **Total Process Features** | 591 (1 Timestamp + 590 Continuous Sensors) | Verified |
| **Duplicate Entity Rows** | 0 duplicates | Passed |
| **Overall Missing-Value Rate** | 4.54% (41,951 missing cells) | Monitored |
| **Zero-Variance Features** | 116 sensors (constant readings across all runs) | **Quarantined** (Dropped from ML) |
| **High-Missingness Features** | 28 sensors (>50% missing values; max: 91.2%) | **Quarantined** (Isolated in Core) |
| **Vetted Candidate Features** | **446 active process variables** | Promoted to Analytics |
| **Operating Time Span** | July 19, 2008 – October 17, 2008 (90 days) | Chronological Validation Enforced |
| **Quality Outcome Balance** | 1,463 Passes (93.36%) vs. 104 Fails (6.64%) | Severe Class Imbalance (14:1) |
| **Overall Health Status** | **WARNING** | Data Quality Gate Triggered |

*Quality Artifacts:* [data_quality_report.txt](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/data/quality/data_quality_report.txt), [data_quality_summary.json](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/data/quality/data_quality_summary.json), [high_missing_columns.csv](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/data/quality/high_missing_columns.csv), [constant_columns.csv](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/data/quality/constant_columns.csv).

---

## 📈 SQL Analytics & Operational Findings

Executing the analytical warehouse views ([run_sql_analytics.py](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/src/transformation/run_sql_analytics.py)) exposed critical factory patterns:

1. **Shift Quality Disparity:**
   * **Evening Shift:** 7.04% defect rate (£18,000 total scrap loss).
   * **Night Shift:** 6.51% defect rate (£14,850 total scrap loss).
   * **Day Shift:** 6.30% defect rate (£13,950 total scrap loss, 93.70% yield).
2. **Maintenance Cycle Anomaly:**
   * **Sunday:** Spike to **10.55% defect rate** vs Tuesday's **4.35%**, indicating equipment cold-start calibration drift after weekend maintenance windows.

---

## 🤖 Machine Learning Benchmarks & Cost Optimization

To prevent time-travel data leakage, models were trained on a **strict chronological 80/20 split** (first 1,253 runs train, subsequent 314 runs test). The probability threshold was tuned against plant economics ($FN \times £450 + FP \times £25$):

| Model | Accuracy | Defect Recall | Precision | PR-AUC | ROC-AUC | Optimal Thresh | Operational Cost | Cost Savings |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Champion (Cost-Sensitive LogReg)** | 73.57% | **88.24%** | **8.43%** | **0.1263** | **0.7092** | **0.140** | **£4,975.00** | **+34.97%** |
| **Balanced Random Forest** | 85.03% | 82.35% | 6.28% | 0.0647 | 0.5274 | 0.090 | £6,575.00 | +14.05% |
| **Gradient Boosting (Class-Weighted)** | 94.59% | 0.00% | 0.00% | 0.0702 | 0.5916 | 0.080 | £7,650.00 | 0.00% |
| **Dummy Majority Baseline** | **94.59%** | **0.00%** | **0.00%** | 0.0541 | 0.5000 | 0.020 | £7,650.00 | 0.00% |

> **The 94.6% Accuracy Trap:** A naive dummy classifier achieves 94.59% accuracy but catches 0% of defects, incurring maximum scrap loss (£7,650). The champion model achieves **88.24% recall** (catching 15 of 17 defects), saving **£2,675 per 300 wafers (34.97% net financial savings)**.

*Model Artifacts:* [champion_quality_model.joblib](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/models/champion_quality_model.joblib), [model_benchmark_results.csv](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/data/processed/model_benchmark_results.csv), [MODEL_CARD.md](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/docs/model_card.md).

---

## 🔍 Explainable AI (SHAP) & Root-Cause Playbooks

SHAP attributions identify which physical chamber parameters drive quality failure risk:

| Sensor Attribute | Mean \|SHAP\| | Physical Equipment Parameter | Prescriptive Engineering Action |
|:---|:---:|:---|:---|
| **Attribute 578** | **1.0381** | Chamber Plasma RF Matching | Inspect capacitor alignment & reflected power impedance |
| **Attribute 429** | **0.5850** | Litho UV Lamp Intensity | Calibrate optical exposure dose and focal budget |
| **Attribute 574** | **0.5196** | Etch Chamber Pressure | Verify turbomolecular pump vibration and roughing line |
| **Attribute 65** | **0.4658** | Chamber Wall Temperature | Inspect cooling water jacket recirculation loop |
| **Attribute 289** | **0.4029** | Base Vacuum Pressure | Clean chamber exhaust throttle valve |

*Visualization:* Generated at [dashboards/shap_feature_importance.png](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/dashboards/shap_feature_importance.png).

---

## 📦 Operational Decision Support & Dynamic Safety Stock

Connecting ML predictions to daily shop-floor workflows ([inventory_operations_logic.py](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/src/forecasting/inventory_operations_logic.py)):

### 1. Automated 3-Tier Lot Dispatch Queue
* **TIER 1 — CRITICAL (Risk $\ge 14\%$):** **HOLD LOT**. Divert to Inline Metrology & Secondary Acoustic Microscopy (£25 check).
* **TIER 2 — ELEVATED ($8\% \le \text{Risk} < 14\%$):** **MONITOR**. Flag tool chamber drift; schedule preventative clean.
* **TIER 3 — NOMINAL (Risk $< 8\%$):** **RELEASE**. Fast-track to downstream metallization and chemical-mechanical planarization.

### 2. Dynamic Safety Stock Sizing
* **Target Delivery:** 1,000 finished wafers/month at a **98.0% service level**.
* **Base Yield:** 93.36% (requires 1,072 gross wafer starts).
* **Dynamic Safety Buffer:** 235 wafers (£28,200 raw substrate value) calibrated against 14-day forecasted scrap volatility ([yield_forecasting.py](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/src/forecasting/yield_forecasting.py)).

---

## 📁 Repository Structure

```text
manufacturing-operations-intelligence/
├── README.md                               # Project documentation & business case
├── requirements.txt                        # Pinned dependencies
├── .gitignore                              # Git exclusion rules
│
├── data/
│   ├── raw/                                # Immutable source data (secom_features_raw, secom_labels_raw)
│   ├── processed/                          # Analytics outputs, matrices, warehouse database
│   └── quality/                            # Data quality reports, column profiles, quarantine lists
│
├── notebooks/
│   └── 01_data_profiling.ipynb             # 10-section end-to-end data profiling analysis
│
├── src/
│   ├── ingestion/download_secom.py         # Reproducible UCI SECOM fetcher
│   ├── quality/generate_quality_report.py  # Automated health scorecard profiler
│   ├── transformation/load_database.py     # Medallion ETL loader (PostgreSQL & SQLite)
│   ├── transformation/run_sql_analytics.py # SQL KPI runner & CSV exporter
│   ├── modelling/feature_selection.py      # Chronological split & Top-50 feature ranking
│   ├── modelling/train_models.py           # Cost-of-Quality benchmark & threshold tuning
│   ├── modelling/explainability_shap.py    # SHAP attribution & engineering action playbook
│   ├── forecasting/yield_forecasting.py    # 14-day rolling yield & scrap volume regressor
│   ├── forecasting/inventory_operations_logic.py # Lot routing & dynamic safety buffer
│   └── pipeline_runner.py                  # End-to-end automated orchestrator
│
├── sql/
│   ├── 01_init_database.sql                # Schema DDL (staging, core, analytics)
│   ├── 02_staging_schema.sql               # Staging tables (JSONB raw telemetry)
│   ├── 03_core_schema.sql                  # Dimensional star schema (Production, Sensor, Quality)
│   ├── 04_analytics_views.sql              # Yield KPIs & sensor governance views
│   └── 05_analytical_queries.sql          # Shift performance & weekly scrap SQL queries
│
├── dashboards/
│   ├── power_bi_data_model_spec.md         # Star schema, DAX measures, & 4-page cockpit spec
│   ├── shap_feature_importance.png         # SHAP attribution plot
│   ├── yield_forecast_14d.png              # 14-day scrap forecast plot
│   └── operational_alerts_summary.png      # Real-time lot risk routing distribution
│
├── architecture/
│   ├── system_architecture.md              # Technical system specs & Mermaid diagrams
│   └── current_vs_future_state_process.md  # Digital transformation sequence maps
│
├── docs/
│   ├── model_card.md                       # Comprehensive ML Model Card
│   └── ktp_interview_and_cv_guide.md       # STAR interview stories, Q&A, and CV bullets
│
└── tests/
    └── __init__.py                         # Test package initialization
```

---

## 🚀 Quickstart & Pipeline Reproduction

### 1. Environment Setup
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows (or: source .venv/bin/activate on Linux/macOS)
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Execute Entire Pipeline in One Command
```bash
python src/pipeline_runner.py
```
This runs all 9 stages end-to-end:
1. Downloads and validates SECOM dataset from UCI
2. Executes data quality profiling and generates quarantine registers
3. Populates dimensional warehouse tables
4. Runs SQL operational analytics queries
5. Conducts chronological split and feature ranking
6. Trains cost-sensitive ML classifiers and tunes decision thresholds
7. Computes SHAP explainability values and maps root-cause playbooks
8. Generates 14-day scrap time-series forecast
9. Simulates dynamic safety stock and outputs lot dispatch alert queue

### 3. Interactive Data Profiling Notebook
Launch Jupyter to explore [01_data_profiling.ipynb](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/notebooks/01_data_profiling.ipynb):
```bash
jupyter notebook notebooks/01_data_profiling.ipynb
```

---

## 🎯 KTP Associate & Career Positioning

This platform was built to demonstrate real-world readiness for **Knowledge Transfer Partnerships (KTP)**, Digital Transformation, and Manufacturing Analytics roles:
* **Enterprise Architecture:** Avoids naive flat-file notebooks; demonstrates production-grade 3-tier data warehousing.
* **Business Acumen:** Replaces generic classification accuracy with financial **Cost of Quality (CoQ)** optimization.
* **Domain Empathy:** Bridges physical factory operations with explainable AI (XAI) and real-time shop-floor lot dispatch.

See the complete [KTP Interview & CV Guide](file:///c:/Users/ZhuanZ1/Desktop/manufacturing-operations-intelligence/docs/ktp_interview_and_cv_guide.md) for full STAR behavioral stories and architectural defense strategies.
