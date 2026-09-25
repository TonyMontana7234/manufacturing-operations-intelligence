# KTP Interview & CV Preparation Guide
## Manufacturing Operations Intelligence Platform

---

## 1. Resume / CV Experience Bullets

Use these impactful, metric-driven bullet points for your CV under **Projects** or **Data Engineering / ML Experience**:

* **Architected an End-to-End Manufacturing Operations Intelligence Platform** integrating 590-sensor semiconductor telemetry (SECOM) across PostgreSQL, Scikit-Learn, SHAP, and Power BI.
* **Engineered an Enterprise 3-Tier PostgreSQL Architecture** (`staging` ➔ `core` ➔ `analytics`) leveraging hybrid JSONB payloads and dimensional modeling to eliminate 590-column wide-table anti-patterns.
* **Developed Automated Data Quality Gates** identifying 116 constant zero-variance features and quarantining 28 high-missingness sensors (>50% missing), establishing zero-failure ingestion pipelines.
* **Trained Cost-Sensitive Yield-Risk Classifiers** with chronological temporal validation, outperforming majority baseline accuracy to achieve **88.24% defect recall** and a **34.97% reduction in scrapped factory inventory (£450/wafer vs £25 metrology check)**.
* **Implemented Explainable AI (SHAP) Diagnostics** to translate complex high-dimensional chamber telemetry into prescriptive maintenance actions for cleanroom shift engineers.
* **Designed Dynamic Safety Stock & 14-Day Forecasting Models** to automate lot routing (Hold/Inspect/Release) and synchronize material ordering with fluctuating production yields.

---

## 2. STAR Interview Stories (KTP / Industry Focus)

### Story 1: Handling Real-World Industrial Data Quality & Architecture
* **Situation:** Semiconductor fabrication generates high-dimensional telemetry with sensor dropouts, calibration drift, and severe class imbalance, making naive modeling prone to silent failure.
* **Task:** Design a robust, scalable data architecture and automated quality gate that prevents corrupt telemetry from polluting downstream analytical and ML pipelines.
* **Action:** 
  1. Profiled the 1,567 observations across 590 sensors, identifying 41,951 missing cells (4.54%) and 116 zero-variance columns.
  2. Implemented a 3-tier PostgreSQL database structure (`staging`, `core`, `analytics`) using JSONB for raw sensor storage and normalized dimensional tables (`dim_production_entity`, `dim_sensor`, `fact_quality_outcome`).
  3. Established an automated quarantine gate that isolates features with >50% missingness while enforcing chronological train/test splitting to prevent time-travel data leakage.
* **Result:** Reduced feature dimensionality from 590 to 446 vetted candidate features with 100% reproducible ETL pipelines and auditable quality logs.

---

### Story 2: Turning Machine Learning into Factory Financial Value (Cost of Quality)
* **Situation:** In high-yield manufacturing (6.64% defect rate), a dummy model predicting "Pass" achieves 93.36% accuracy but provides zero operational utility because every defect slips into expensive downstream packaging.
* **Task:** Build an operational failure-risk prediction system that optimizes plant economics rather than generic classification metrics.
* **Action:** 
  1. Formulated a financial Cost-of-Quality (CoQ) objective function: False Negatives cost £450 in scrapped silicon, while False Positives cost £25 for secondary metrology re-testing.
  2. Benchmarked cost-weighted classifiers against chronological holdout data.
  3. Swept decision boundaries to discover the cost-optimal operating threshold (0.14) rather than using the default 0.5 probability cutoff.
* **Result:** Achieved **88.24% defect recall**, catching 15 of 17 defects in the test batch and delivering a **34.97% net financial cost reduction (£4,975 vs £7,650)**.

---

### Story 3: Bridging Data Science with Shop-Floor Operations (Explainable AI & BI)
* **Situation:** Factory operators and cleanroom supervisors often reject "black-box" machine learning predictions because they do not explain which machine or chamber caused the risk.
* **Task:** Provide transparent, actionable root-cause diagnoses and embed them into daily shop-floor dispatch workflows.
* **Action:** 
  1. Computed SHAP values for all test predictions to isolate individual sensor contributions.
  2. Mapped the top predictive variables (e.g. `Attribute 578` plasma RF impedance, `Attribute 429` UV lamp intensity) to concrete physical maintenance playbooks.
  3. Designed a 4-page Power BI executive and engineering cockpit and an automated 3-tier lot routing mechanism (Tier 1: Hold & Metrology, Tier 2: Elevated Drift Monitor, Tier 3: Fast-Track Release).
* **Result:** Enabled shift supervisors to intervene at early processing stages, eliminating 4–7 days of post-mortem committee review.

---

## 3. High-Probability Technical Interview Questions & Model Answers

#### Q1: "Why did you use a chronological split instead of Stratified K-Fold Cross-Validation?"
> *"In semiconductor manufacturing, sensor telemetry exhibits non-stationary temporal drift due to tool wear, gas depletion, and scheduled maintenance over the 90-day production run. If we apply random Stratified K-Fold, the model trains on future runs to predict past runs, causing severe temporal data leakage. A chronological split (80% training / 20% holdout) accurately simulates real deployment, where the model only ever learns from historical runs."*

#### Q2: "With 94.6% baseline accuracy, why did your champion model have 73.6% accuracy?"
> *"Because in imbalanced industrial quality control, raw accuracy is a dangerous illusion. A dummy classifier that predicts 100% of wafers will pass achieves 94.59% accuracy on the test set, but its recall is 0.0%—meaning all 17 defects slip through, inflicting £7,650 in scrap losses. By tuning our probability threshold to 0.14, our model caught 88.24% of all defects. The slight increase in false alarms (£25 re-test fee) was overwhelmingly outweighed by the defect scrap savings (£450 saved per caught defect), cutting total operational cost by 34.97%."*

#### Q3: "Why did you use PostgreSQL JSONB for staging instead of 590 separate columns?"
> *"PostgreSQL tables with 590 individual columns create significant schema maintenance overhead, brittle DDL migrations, and trigger TOAST pointer compression on wide tuples. In modern industrial IoT, sensor instrumentation changes between chambers. By storing raw sensor reads in a flexible, indexed JSONB column in `staging.secom_raw` while extracting vetted, typed features into normalized tables in `core` and `analytics`, we achieve the flexibility of NoSQL with the relational integrity of an enterprise warehouse."*
