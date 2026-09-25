-- ==============================================================================
-- 03_core_schema.sql
-- Manufacturing Operations Intelligence Platform
-- Core Layer: Normalized Dimensional Architecture
-- ==============================================================================

DROP TABLE IF EXISTS core.fact_quality_outcome CASCADE;
DROP TABLE IF EXISTS core.dim_sensor CASCADE;
DROP TABLE IF EXISTS core.dim_production_entity CASCADE;

-- 1. Production Entity Dimension
-- Tracks each manufactured unit/wafer, operational timestamp, shift, and calendar hierarchy
CREATE TABLE core.dim_production_entity (
    production_id           INTEGER PRIMARY KEY,
    run_timestamp           TIMESTAMP WITH TIME ZONE NOT NULL,
    run_date                DATE GENERATED ALWAYS AS (run_timestamp::DATE) STORED,
    run_hour                INTEGER GENERATED ALWAYS AS (EXTRACT(HOUR FROM run_timestamp)::INTEGER) STORED,
    shift_code              VARCHAR(20),                -- 'DAY_SHIFT', 'EVENING_SHIFT', 'NIGHT_SHIFT'
    day_name                VARCHAR(15),                -- 'Monday', etc.
    week_of_year            INTEGER,
    month_name              VARCHAR(15)
);

CREATE INDEX idx_core_entity_date ON core.dim_production_entity (run_date);
CREATE INDEX idx_core_entity_shift ON core.dim_production_entity (shift_code);

-- 2. Sensor Dimension Table
-- Metadata and data quality governance register for all 590 manufacturing sensors
CREATE TABLE core.dim_sensor (
    sensor_id               INTEGER PRIMARY KEY,        -- 1 to 590
    sensor_code             VARCHAR(50) NOT NULL UNIQUE,-- e.g., 'Attribute 1'
    sensor_alias            VARCHAR(100),               -- e.g., 'chamber_temp_primary'
    category                VARCHAR(50) DEFAULT 'INSPECTION_METRIC',
    is_constant             BOOLEAN DEFAULT FALSE,
    missing_rate_pct        NUMERIC(5,2) NOT NULL,
    is_quarantined          BOOLEAN DEFAULT FALSE,      -- TRUE if >50% missing or constant
    quarantine_reason       TEXT,
    mean_val                DOUBLE PRECISION,
    std_val                 DOUBLE PRECISION,
    min_val                 DOUBLE PRECISION,
    max_val                 DOUBLE PRECISION,
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_core_sensor_quarantine ON core.dim_sensor (is_quarantined);

-- 3. Quality Outcome Fact Table
-- Ground-truth quality labels mapped to operational consequence and cost definitions
CREATE TABLE core.fact_quality_outcome (
    production_id           INTEGER PRIMARY KEY REFERENCES core.dim_production_entity(production_id) ON DELETE CASCADE,
    raw_label               INTEGER NOT NULL,           -- -1 or 1
    is_defect               BOOLEAN NOT NULL,           -- TRUE if fail (1), FALSE if pass (-1)
    defect_classification   VARCHAR(30) NOT NULL,       -- 'CONFORMING' vs 'NON_CONFORMING'
    estimated_scrap_cost    NUMERIC(10,2) DEFAULT 0.00, -- Financial impact modeling
    reinspection_flag       BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_core_quality_defect ON core.fact_quality_outcome (is_defect);

COMMENT ON TABLE core.dim_production_entity IS 'Master entity dimension for semiconductor production runs';
COMMENT ON TABLE core.dim_sensor IS 'Governance register maintaining operational status and data quality flags for each sensor';
COMMENT ON TABLE core.fact_quality_outcome IS 'Quality audit facts with business cost parameters';
