-- ==============================================================================
-- 04_analytics_views.sql
-- Manufacturing Operations Intelligence Platform
-- Analytics Layer: Operational Yield KPIs, BI Feeds, & Feature Store
-- ==============================================================================

-- 1. Daily Production Yield & Quality Defect Rates
-- Aggregates total manufactured units, pass/fail counts, yield % and scrap impact
CREATE OR REPLACE VIEW analytics.v_production_yield_daily AS
SELECT
    p.run_date,
    COUNT(p.production_id) AS total_units_produced,
    SUM(CASE WHEN q.is_defect = FALSE THEN 1 ELSE 0 END) AS conforming_units,
    SUM(CASE WHEN q.is_defect = TRUE THEN 1 ELSE 0 END) AS defective_units,
    ROUND(
        (SUM(CASE WHEN q.is_defect = FALSE THEN 1 ELSE 0 END)::NUMERIC / COUNT(p.production_id)) * 100,
        2
    ) AS yield_rate_pct,
    ROUND(
        (SUM(CASE WHEN q.is_defect = TRUE THEN 1 ELSE 0 END)::NUMERIC / COUNT(p.production_id)) * 100,
        2
    ) AS defect_rate_pct,
    SUM(q.estimated_scrap_cost) AS total_scrap_cost_gbp
FROM core.dim_production_entity p
JOIN core.fact_quality_outcome q ON p.production_id = q.production_id
GROUP BY p.run_date
ORDER BY p.run_date ASC;

-- 2. Shift Performance Analytics
-- Compares yield and defect rates across Day, Evening, and Night operating shifts
CREATE OR REPLACE VIEW analytics.v_shift_performance AS
SELECT
    p.shift_code,
    COUNT(p.production_id) AS total_runs,
    SUM(CASE WHEN q.is_defect = TRUE THEN 1 ELSE 0 END) AS defect_count,
    ROUND(
        (SUM(CASE WHEN q.is_defect = TRUE THEN 1 ELSE 0 END)::NUMERIC / COUNT(p.production_id)) * 100,
        2
    ) AS shift_defect_rate_pct
FROM core.dim_production_entity p
JOIN core.fact_quality_outcome q ON p.production_id = q.production_id
GROUP BY p.shift_code
ORDER BY shift_defect_rate_pct DESC;

-- 3. Sensor Health & Data Quality Status
-- Exposes active vs quarantined sensor counts for process engineering review
CREATE OR REPLACE VIEW analytics.v_sensor_governance_summary AS
SELECT
    COUNT(*) AS total_sensors,
    SUM(CASE WHEN is_constant = TRUE THEN 1 ELSE 0 END) AS constant_sensors,
    SUM(CASE WHEN missing_rate_pct > 50.0 THEN 1 ELSE 0 END) AS high_missing_sensors,
    SUM(CASE WHEN is_quarantined = TRUE THEN 1 ELSE 0 END) AS quarantined_sensors,
    SUM(CASE WHEN is_quarantined = FALSE THEN 1 ELSE 0 END) AS candidate_features_for_ml
FROM core.dim_sensor;

COMMENT ON VIEW analytics.v_production_yield_daily IS 'Daily aggregated manufacturing yield and scrap KPIs for executive dashboards';
COMMENT ON VIEW analytics.v_shift_performance IS 'Operational shift comparison identifying shift-specific yield excursions';
COMMENT ON VIEW analytics.v_sensor_governance_summary IS 'Sensor data quality register summarizing valid vs quarantined features';
