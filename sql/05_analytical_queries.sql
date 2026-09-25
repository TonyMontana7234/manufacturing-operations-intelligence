-- ==============================================================================
-- 05_analytical_queries.sql
-- Manufacturing Operations Intelligence Platform
-- Analytical Queries & KPI Benchmarks
-- ==============================================================================

-- 1. Operational Shift Defect Comparison
-- Evaluates process stability across operating shifts
SELECT 
    p.shift_code,
    COUNT(p.production_id) AS total_runs,
    SUM(CASE WHEN q.is_defect = TRUE THEN 1 ELSE 0 END) AS defective_units,
    ROUND(
        (SUM(CASE WHEN q.is_defect = TRUE THEN 1 ELSE 0 END)::NUMERIC / COUNT(p.production_id)) * 100, 
        2
    ) AS defect_rate_pct,
    ROUND(
        (SUM(CASE WHEN q.is_defect = FALSE THEN 1 ELSE 0 END)::NUMERIC / COUNT(p.production_id)) * 100, 
        2
    ) AS yield_rate_pct,
    SUM(q.estimated_scrap_cost) AS total_scrap_cost_gbp
FROM core.dim_production_entity p
JOIN core.fact_quality_outcome q ON p.production_id = q.production_id
GROUP BY p.shift_code
ORDER BY defect_rate_pct DESC;


-- 2. Weekly Production & Scrap Cost Exposure
-- Tracks quality excursions by calendar week to monitor macro drift
SELECT 
    p.week_of_year,
    MIN(p.run_date) AS week_start_date,
    COUNT(p.production_id) AS total_wafers,
    SUM(CASE WHEN q.is_defect = TRUE THEN 1 ELSE 0 END) AS scrap_wafers,
    ROUND(
        (SUM(CASE WHEN q.is_defect = TRUE THEN 1 ELSE 0 END)::NUMERIC / COUNT(p.production_id)) * 100, 
        2
    ) AS weekly_defect_rate_pct,
    SUM(q.estimated_scrap_cost) AS weekly_scrap_cost_gbp
FROM core.dim_production_entity p
JOIN core.fact_quality_outcome q ON p.production_id = q.production_id
GROUP BY p.week_of_year
ORDER BY p.week_of_year ASC;


-- 3. Day of Week Quality Variance
-- Identifies maintenance cycle anomalies (e.g. Monday startup vs weekend shifts)
SELECT 
    p.day_name,
    COUNT(p.production_id) AS total_wafers,
    SUM(CASE WHEN q.is_defect = TRUE THEN 1 ELSE 0 END) AS defect_count,
    ROUND(
        (SUM(CASE WHEN q.is_defect = TRUE THEN 1 ELSE 0 END)::NUMERIC / COUNT(p.production_id)) * 100, 
        2
    ) AS defect_rate_pct
FROM core.dim_production_entity p
JOIN core.fact_quality_outcome q ON p.production_id = q.production_id
GROUP BY p.day_name
ORDER BY defect_rate_pct DESC;


-- 4. Sensor Quality Governance Status
-- Audits total available instrumentation and quarantine rates for compliance
SELECT 
    COUNT(*) AS total_instrumentation_sensors,
    SUM(CASE WHEN is_constant = TRUE THEN 1 ELSE 0 END) AS constant_zero_variance,
    SUM(CASE WHEN missing_rate_pct > 50.0 THEN 1 ELSE 0 END) AS severe_missing_gt_50pct,
    SUM(CASE WHEN is_quarantined = TRUE THEN 1 ELSE 0 END) AS total_quarantined,
    SUM(CASE WHEN is_quarantined = FALSE THEN 1 ELSE 0 END) AS vetted_ml_features
FROM core.dim_sensor;
