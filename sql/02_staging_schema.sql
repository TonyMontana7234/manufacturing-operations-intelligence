-- ==============================================================================
-- 02_staging_schema.sql
-- Manufacturing Operations Intelligence Platform
-- Staging Layer: Raw Data Ingestion & Quality Logs
-- ==============================================================================

-- Drop existing staging tables if recreating
DROP TABLE IF EXISTS staging.data_quality_audit_log CASCADE;
DROP TABLE IF EXISTS staging.secom_raw CASCADE;

-- 1. Raw Telemetry Ingestion Table
-- Utilizes a hybrid model: relational business keys + JSONB sensor payload
-- This avoids unwieldy 590-column wide tables while retaining lossless precision.
CREATE TABLE staging.secom_raw (
    production_id           INTEGER PRIMARY KEY,
    event_timestamp         TIMESTAMP WITH TIME ZONE NOT NULL,
    quality_label           INTEGER NOT NULL,          -- -1 = Pass, 1 = Fail
    sensor_data             JSONB NOT NULL,            -- Raw 590 sensor readings key-value
    ingested_at             TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_source             VARCHAR(100) DEFAULT 'UCI_SECOM_ID_179'
);

CREATE INDEX idx_staging_secom_ts ON staging.secom_raw (event_timestamp);
CREATE INDEX idx_staging_secom_label ON staging.secom_raw (quality_label);
CREATE INDEX idx_staging_secom_sensor_gin ON staging.secom_raw USING GIN (sensor_data);

COMMENT ON TABLE staging.secom_raw IS 'Landing table for immutable raw manufacturing telemetry records';
COMMENT ON COLUMN staging.secom_raw.sensor_data IS 'Lossless JSONB container storing raw measurements for Attribute 1 through 590';

-- 2. Data Quality Audit Log Table
-- Automatically captures schema-level health metrics, nullity, and variance checks
CREATE TABLE staging.data_quality_audit_log (
    log_id                  SERIAL PRIMARY KEY,
    batch_run_id            VARCHAR(64) NOT NULL,
    check_timestamp         TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    dataset_name            VARCHAR(50) DEFAULT 'SECOM',
    total_records           INTEGER NOT NULL,
    total_features          INTEGER NOT NULL,
    duplicate_rows          INTEGER DEFAULT 0,
    overall_missing_pct     NUMERIC(5,2) NOT NULL,
    high_missing_cols_count INTEGER NOT NULL,
    constant_cols_count     INTEGER NOT NULL,
    pass_count              INTEGER NOT NULL,
    fail_count              INTEGER NOT NULL,
    quality_status          VARCHAR(20) NOT NULL,      -- 'PASS', 'WARNING', 'FAIL'
    notes                   TEXT
);

COMMENT ON TABLE staging.data_quality_audit_log IS 'Historical audit trail of data quality profile runs prior to core promotion';
