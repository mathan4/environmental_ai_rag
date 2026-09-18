"""
The retrieval layer combines two knowledge sources on purpose:

1. STRUCTURED lookup (PostgreSQL interventions table) — filtered by the reasoning
   engine's detected issue tags (any soil/climate/land-use/human-impact issue the
   engine can name — not hardcoded to any one metric). This is where numeric
   claims (% ranges, time horizons, sources) come from.
2. SEMANTIC search (pgvector over knowledge documents in PostgreSQL) — provides the scientific
   reasoning/mechanism narrative that supports and contextualizes those numbers.

The LLM downstream is instructed to synthesize from both, not invent new figures.
"""
from db.connection import get_connection
from rag.embeddings import embed_text
from rag.vector_store import search as vector_search


def get_structured_interventions(detected_issues: list[str]) -> list[dict]:
    """
    Returns interventions whose targets_issues overlaps with the issue tags the
    reasoning engine actually detected for this input.
    """
    if not detected_issues:
        return []

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM interventions")
            rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    detected_set = set(detected_issues)
    filtered = []
    for r in rows:
        row_tags = set(r["targets_issues"].split(","))
        if row_tags & detected_set:
            filtered.append(r)
    return filtered


def get_metric_thresholds() -> dict:
    """Reference thresholds (low/high bounds) for interpreting raw metric values."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM metric_thresholds")
            return {r["metric"]: dict(r) for r in cur.fetchall()}
    finally:
        conn.close()



def semantic_search(query: str, top_k: int = 4) -> list[dict]:
    """Retrieves relevant scientific-reasoning passages from the knowledge documents."""
    q_vec = embed_text(query)
    return vector_search(q_vec, top_k=top_k)
