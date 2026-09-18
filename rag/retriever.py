"""
The retrieval layer combines two knowledge sources on purpose:

1. STRUCTURED lookup (SQLite interventions table) — filtered by the reasoning
   engine's detected issues (land use, rainfall, SOC level). This is where numeric
   claims (% ranges, time horizons, sources) come from.
2. SEMANTIC search (FAISS over knowledge documents) — provides the scientific
   reasoning/mechanism narrative that supports and contextualizes those numbers.

The LLM downstream is instructed to synthesize from both, not invent new figures.
"""
from db.connection import get_connection
from rag.embeddings import embed_text
from rag.vector_store import search as vector_search


def get_structured_interventions(land_use: str = None, rainfall: str = None, soc: float = None) -> list[dict]:
    """Filters the structured benchmark table by applicability to the current inputs."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM interventions")
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    filtered = []
    for r in rows:
        if r["applicable_land_use"] not in (None, "any") and land_use and r["applicable_land_use"] != land_use:
            continue
        if r["applicable_rainfall"] not in (None, "any") and rainfall and r["applicable_rainfall"] != rainfall:
            continue
        if r["applicable_soc_max"] is not None and soc is not None and soc > r["applicable_soc_max"]:
            continue
        filtered.append(r)
    return filtered


def get_metric_thresholds() -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM metric_thresholds")
        return {r["metric"]: dict(r) for r in cur.fetchall()}
    finally:
        conn.close()


def semantic_search(query: str, top_k: int = 4) -> list[dict]:
    """Retrieves relevant scientific-reasoning passages from the knowledge documents."""
    q_vec = embed_text(query)
    return vector_search(q_vec, top_k=top_k)
