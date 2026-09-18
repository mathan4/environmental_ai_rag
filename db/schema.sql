-- PostgreSQL + pgvector Schema definition for Eco Advisor

CREATE EXTENSION IF NOT EXISTS vector;

-- Structured knowledge layer: quantified intervention benchmarks.
CREATE TABLE IF NOT EXISTS interventions (
    id                  SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    action_summary      TEXT NOT NULL,
    mechanism           TEXT NOT NULL,       -- WHY it works (scientific reasoning)
    impacted_metric     TEXT NOT NULL,       -- e.g. 'soil_organic_carbon', 'pollinator_diversity'
    effect_low_pct      DOUBLE PRECISION,
    effect_high_pct     DOUBLE PRECISION,
    time_horizon        TEXT NOT NULL,       -- 'short' | 'medium' | 'long'
    time_horizon_detail TEXT,                -- e.g. '2-3 years'
    confidence          TEXT NOT NULL,       -- 'high' | 'medium' | 'low'
    source_org          TEXT NOT NULL,       -- e.g. 'FAO', 'IPCC', 'CBD/IPBES'
    targets_issues      TEXT NOT NULL
);

-- Registry of ingested structured datasets (CSV). Actual data lives in its own
-- dynamically-created table (named after the dataset); this tracks what exists.
CREATE TABLE IF NOT EXISTS dataset_registry (
    dataset_name  TEXT PRIMARY KEY,   -- sanitized table name holding the actual rows
    source_file   TEXT NOT NULL,
    columns       TEXT NOT NULL,      -- comma-separated column list, for quick reference
    row_count     INTEGER NOT NULL,
    loaded_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Reference thresholds for interpreting raw input values (used by the reasoning engine,
-- not the LLM, to decide which issues are actually present before retrieval).
CREATE TABLE IF NOT EXISTS metric_thresholds (
    metric      TEXT PRIMARY KEY,
    low_bound   DOUBLE PRECISION,
    high_bound  DOUBLE PRECISION,
    unit        TEXT,
    notes       TEXT
);

-- Semantic vector store table replacing local FAISS index
CREATE TABLE IF NOT EXISTS rag_documents (
    id          SERIAL PRIMARY KEY,
    source      TEXT NOT NULL,
    page        INTEGER,
    text        TEXT NOT NULL,
    embedding   vector(384)
);

CREATE INDEX IF NOT EXISTS rag_documents_embedding_hnsw_idx
    ON rag_documents USING hnsw (embedding vector_cosine_ops);