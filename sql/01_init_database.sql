-- ==============================================================================
-- 01_init_database.sql
-- Manufacturing Operations Intelligence Platform
-- Database & Schema Initialization
-- ==============================================================================

-- Create schemas to enforce a 3-tier data architecture:
-- 1. STAGING   : Raw ingested telemetry and staging tables
-- 2. CORE      : Normalized dimensional entities (Production, Sensors, Quality)
-- 3. ANALYTICS : Aggregated operational views, ML feature tables, and BI feeds

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;

COMMENT ON SCHEMA staging IS 'Raw data import layer maintaining immutable telemetry payloads and quality audit logs';
COMMENT ON SCHEMA core IS 'Cleaned, normalized enterprise dimensional model (Production entities, Sensors, Quality outcomes)';
COMMENT ON SCHEMA analytics IS 'Curated analytical views, ML feature matrices, and Power BI operational data models';
