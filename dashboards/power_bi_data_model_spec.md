# Power BI Semantic Model & Dashboard Specification
## Manufacturing Operations Intelligence Platform

---

## 1. Enterprise Star Schema Architecture

```
                  ┌──────────────────────────────┐
                  │    dim_production_entity     │
                  ├──────────────────────────────┤
                  │ PK  production_id            │
                  │     run_timestamp            │
                  │     run_date                 │
                  │     run_hour                 │
                  │     shift_code               │
                  │     day_name                 │
                  │     week_of_year             │
                  │     month_name               │
                  └──────────────┬───────────────┘
                                 │ 1
                                 │
                                 │ *
                  ┌──────────────┴───────────────┐
                  │     fact_quality_outcome     │
                  ├──────────────────────────────┤
                  │ PK  production_id            │
                  │     raw_label                │
                  │     is_defect                │
                  │     defect_classification    │
                  │     estimated_scrap_cost     │
                  │     reinspection_flag        │
                  └──────────────┬───────────────┘
                                 │ 1
                                 │
                                 │ 1
                  ┌──────────────┴───────────────┐
                  │   fact_operational_alerts    │
                  ├──────────────────────────────┤
                  │ PK  lot_id                   │
                  │     failure_risk_pct         │
                  │     risk_tier                │
                  │     operational_action       │
                  │     alert_urgency            │
                  └──────────────────────────────┘
```

---

## 2. Core DAX Measures Library

### Base Volume & Conformance Measures
```dax
Total Wafers Produced = 
COUNTROWS('fact_quality_outcome')

Conforming Wafers = 
CALCULATE(
    COUNTROWS('fact_quality_outcome'),
    'fact_quality_outcome'[is_defect] = FALSE
)

Defective Wafers = 
CALCULATE(
    COUNTROWS('fact_quality_outcome'),
    'fact_quality_outcome'[is_defect] = TRUE
)
```

### Yield & Quality Performance Rates
```dax
Yield Rate % = 
DIVIDE([Conforming Wafers], [Total Wafers Produced], 0)

Defect Rate % = 
DIVIDE([Defective Wafers], [Total Wafers Produced], 0)

Rolling 7D Defect Rate % = 
CALCULATE(
    [Defect Rate %],
    DATESINPERIOD(
        'dim_production_entity'[run_date],
        LASTDATE('dim_production_entity'[run_date]),
        -7,
        DAY
    )
)
```

### Financial Cost of Quality (CoQ)
```dax
Total Scrap Loss (£) = 
SUM('fact_quality_outcome'[estimated_scrap_cost])

Baseline Unmitigated Risk (£) = 
[Defective Wafers] * 450.0

Mitigated Operational Cost (£) = 
VAR FalseNegatives = CALCULATE(COUNTROWS('fact_operational_alerts'), 'fact_operational_alerts'[risk_tier] = "TIER_3_NOMINAL", 'fact_quality_outcome'[is_defect] = TRUE)
VAR FalsePositives = CALCULATE(COUNTROWS('fact_operational_alerts'), 'fact_operational_alerts'[risk_tier] = "TIER_1_CRITICAL", 'fact_quality_outcome'[is_defect] = FALSE)
RETURN
(FalseNegatives * 450.0) + (FalsePositives * 25.0)

Financial Savings Delivered (£) = 
[Baseline Unmitigated Risk (£)] - [Mitigated Operational Cost (£)]
```

---

## 3. Four-Page Dashboard Implementation Blueprint

### Page 1 — Executive Operations Cockpit
* **Target Audience:** VP of Manufacturing, Operations Director, Plant Manager
* **Key Visuals:**
  * **KPI Cards:** Overall Yield (93.36%), Total Scrap (£46,800), Cost Savings via ML (£2,675), Active Sensor Count (446).
  * **Time-Series Chart:** Daily Yield Rate vs Target Line (95.0%).
  * **Matrix Table:** Shift Performance breakdown (`DAY_SHIFT`, `EVENING_SHIFT`, `NIGHT_SHIFT`) highlighting evening excursion rates.

### Page 2 — Engineering Metrology & Root-Cause Analysis
* **Target Audience:** Process Integration Engineers, Metrology Leads
* **Key Visuals:**
  * **Horizontal Bar Chart:** Top 15 Process Sensors driving risk (SHAP attribution values).
  * **Sensor Drift Scatterplot:** Attribute 578 vs Attribute 429 color-coded by Defect outcome.
  * **Prescriptive Action Table:** Real-time lookup of recommended maintenance playbooks based on anomalous sensor readings.

### Page 3 — 14-Day Demand & Scrap Forecasting
* **Target Audience:** Production Planners, Material Supply Officers
* **Key Visuals:**
  * **Forecasting Ribbon Chart:** 14-day projected defect counts and confidence bounds.
  * **Dynamic Starts Calculator:** Real-time slider adjusting target finished wafers and auto-calculating required gross starts and safety buffers.

### Page 4 — Real-Time Lot Dispatch & Alert Queue
* **Target Audience:** Cleanroom Shift Supervisors, Production Floor Dispatchers
* **Key Visuals:**
  * **Status Donut Chart:** % of Lots in Tier 1 (Hold), Tier 2 (Elevated), Tier 3 (Release).
  * **Interactive Dispatch Table:** Sortable by Risk %, Alert Urgency, and Recommended Floor Action.
