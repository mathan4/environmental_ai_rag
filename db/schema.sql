-- Structured knowledge layer: quantified intervention benchmarks.
-- This is deliberately separate from the free-text RAG documents so the system
-- can ground numeric claims (% improvements, time horizons) in structured data
-- rather than letting the LLM invent figures.

CREATE TABLE IF NOT EXISTS interventions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    action_summary      TEXT NOT NULL,
    mechanism           TEXT NOT NULL,       -- WHY it works (scientific reasoning)
    impacted_metric     TEXT NOT NULL,       -- e.g. 'soil_organic_carbon', 'pollinator_diversity'
    effect_low_pct      REAL,
    effect_high_pct     REAL,
    time_horizon        TEXT NOT NULL,       -- 'short' | 'medium' | 'long'
    time_horizon_detail TEXT,                -- e.g. '2-3 years'
    confidence          TEXT NOT NULL,       -- 'high' | 'medium' | 'low'
    source_org          TEXT NOT NULL,       -- e.g. 'FAO', 'IPCC', 'CBD/IPBES'
    -- Comma-separated issue tags this intervention responds to, matching the
    -- `issue` keys produced by reasoning/multi_metric_engine.py (e.g.
    -- 'low_soil_organic_carbon,low_rainfall_stress'). Generic replacement for the
    -- old applicable_land_use/applicable_rainfall/applicable_soc_max columns --
    -- adding a new soil (or any) metric no longer needs a schema change, just a
    -- new issue tag on both the reasoning-engine side and here.
    targets_issues      TEXT NOT NULL
);

-- Registry of ingested structured datasets (CSV). Actual data lives in its own
-- dynamically-created table (named after the dataset); this tracks what exists.
CREATE TABLE IF NOT EXISTS dataset_registry (
    dataset_name  TEXT PRIMARY KEY,   -- sanitized table name holding the actual rows
    source_file   TEXT NOT NULL,
    columns       TEXT NOT NULL,      -- comma-separated column list, for quick reference
    row_count     INTEGER NOT NULL,
    loaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reference thresholds for interpreting raw input values (used by the reasoning engine,
-- not the LLM, to decide which issues are actually present before retrieval).
CREATE TABLE IF NOT EXISTS metric_thresholds (
    metric      TEXT PRIMARY KEY,
    low_bound   REAL,
    high_bound  REAL,
    unit        TEXT,
    notes       TEXT
);