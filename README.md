# Eco Advisor — AI Environmental Scientist System

A conversational system that reasons across soil, water, land-use, and biodiversity
variables together, grounds every recommendation in structured benchmark data and
retrieved scientific-reasoning passages, and asks clarifying questions when it
doesn't have enough information — rather than a plain LLM chatbot guessing.

## Why it's not "just a prompt"

Three separable layers, each doing a distinct job:

1. **Structured knowledge (PostgreSQL `interventions` table)** — quantified
   intervention benchmarks: effect ranges (%), time horizons, confidence, and
   sources. The LLM is instructed to use only these numbers, never invent its own.
   Interventions are matched to a query by **issue tags** (`targets_issues` column),
   not hardcoded field names — see "Soil health is multi-factor" below.
2. **Semantic knowledge (PostgreSQL `pgvector` in `rag_documents` table)** — scientific-reasoning
   passages (why things work, how variables interact), chunked and embedded from
   `knowledge/documents/*.md`, retrieved by vector similarity (`<=>`) to the detected issues.
3. **Multi-metric reasoning (`reasoning/multi_metric_engine.py`)** — plain Python
   rules that decide which cross-variable issues are actually present (e.g. low SOC
   *and* low rainfall compound each other) *before* anything is retrieved or sent to
   the LLM. This is what forces every recommendation to connect ≥2 variables instead
   of reasoning about one number in isolation.

The LLM (Groq) only runs the final synthesis step: turning the already-retrieved,
already-linked evidence into a structured, readable response. It's not asked to
recall facts from its own training — it's constrained to the evidence handed to it.

## Architecture

```
User text / JSON  ──►  input_parser.py  ──►  Session memory (multi-turn)
                                                   │
                                    missing required fields?
                                           │              │
                                         yes              no
                                           │              │
                                  ask clarifying    multi_metric_engine.py
                                    question         (finds linked issues)
                                                           │
                                           ┌───────────────┴───────────────┐
                                           ▼                               ▼
                              PostgreSQL structured lookup      PostgreSQL pgvector search
                              (interventions, filtered           (rag_documents table,
                               by issue tags)                    cosine similarity)
                                           │                               │
                                           └───────────────┬───────────────┘
                                                           ▼
                                              Groq synthesis (constrained
                                              to given evidence + sources)
                                                           │
                                                           ▼
                                          Structured JSON: recommendations,
                                          impacted metrics, time horizon,
                                          confidence, sources, variable links
```

## Setup

```bash
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env      # fill in GROQ_API_KEY and PostgreSQL connection credentials

python build_knowledge_base.py   # initializes PostgreSQL schema, seeds benchmarks, and builds pgvector index
```

## Running it

```bash
# Launch Streamlit Web UI (Interactive Web Application)
streamlit run app.py

# CLI Commands:
python main.py example      # runs the exact example from the spec (SOC 0.3%, low rainfall,
                             # monoculture wheat, semi-arid)

python main.py chat         # interactive multi-turn conversation

python main.py json example_input.json   # structured JSON input, single-shot
```

### Multi-turn clarifying-question behavior

Try this in `python main.py chat`:
```
You: Biodiversity is declining on my land
```
It won't guess — it'll ask for the missing required fields (soil organic carbon,
rainfall, land use). Provide them in your next message and it'll remember the first
message's context and proceed:
```
You: soil organic carbon is 0.3%, rainfall is low, we grow monoculture wheat
```

## Soil health is multi-factor, not just organic carbon

Soil health inputs are `soil_organic_carbon_pct`, `soil_ph`, and `soil_moisture_pct`
(all optional except SOC, which is required). Each has its own threshold row in
`metric_thresholds` (`db/seed_data.py`'s `METRIC_THRESHOLDS`) — the reasoning engine
reads bounds from there rather than hardcoding them, so adding a fourth soil metric
means adding a threshold row and an `analyze()` check, not touching the intervention
matching logic at all.

Interventions declare which issue tags they respond to (`targets_issues`, comma-
separated), matching the `issue` keys `reasoning/multi_metric_engine.py`'s `analyze()`
produces (`low_soil_organic_carbon`, `soil_ph_imbalance`, `low_soil_moisture`, etc.).
`rag/retriever.py`'s `get_structured_interventions()` just intersects detected tags
against the table — no per-metric filter columns to maintain.

## Extending the knowledge base

- **Add real research papers/reports**: drop PDFs into `knowledge/papers/`, then
  re-run `python build_knowledge_base.py`. Each page becomes its own citable chunk —
  retrieved evidence will show as `[filename.pdf, p.14]` instead of just a filename,
  so recommendations can point at an exact page.
- **Add structured datasets**: drop CSVs into `knowledge/datasets/` (a sample is
  included — `sample_regional_survey.csv`), then re-run the build script. Each CSV
  becomes its own queryable SQLite table (e.g. `dataset_sample_regional_survey`),
  registered in `dataset_registry`. Query it directly:
  ```python
  from knowledge.ingestion.csv_loader import query_dataset, list_datasets
  list_datasets()  # see what's loaded
  query_dataset("dataset_sample_regional_survey", filters={"land_use": "agroforestry"})
  ```
  This is separate from the curated `interventions` table (which holds vetted,
  citable benchmarks) — CSVs are raw reference data you can inspect and later
  promote specific findings into `db/seed_data.py` once you've validated them.
- **Add more curated structured benchmarks**: edit `db/seed_data.py`'s
  `INTERVENTIONS` list — give each entry a `targets_issues` list matching issue tags
  from `reasoning/multi_metric_engine.py`'s `analyze()` (add a new tag there too if
  it's a genuinely new issue) — then re-run `python build_knowledge_base.py`.
- Add geo-coordinates: the `region_type` field currently accepts a text label
  (semi-arid, tropical, etc.); wiring this to real geo-coordinates would mean adding
  a climate-zone lookup (e.g. via a koppen-climate API) that maps lat/lon to a
  `region_type` value before it reaches the reasoning engine — not implemented here,
  but the engine already expects a mapped label, so the integration point is `main.py`'s
  input handling.

## Known simplifications (given as a working baseline, not a finished product)

- `conversation/input_parser.py` uses regex/keyword extraction from free text, not an
  LLM-based extractor — transparent and debuggable, but will miss unusual phrasings.
  Structured JSON input bypasses this entirely and is more reliable.
- The structured intervention dataset (`db/seed_data.py`) is a starter set of ~8
  interventions with figures grounded in commonly-cited FAO/IPCC/CBD ranges — for a
  production system this should be expanded and each figure traced to a specific,
  citable report rather than general guidance.
