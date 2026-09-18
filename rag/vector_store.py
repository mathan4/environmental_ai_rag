"""
PostgreSQL + pgvector backed vector store for knowledge documents.
"""
from db.connection import get_connection, init_schema


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    """Simple sliding-window chunking by characters."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c]


def build_index(entries: list[dict]) -> None:
    """
    entries: list of {"source": str, "page": int|None, "text": str} — one entry per
    raw document (markdown file) or page (PDF page). Each entry is chunked, and every
    resulting chunk keeps its source/page so retrieved evidence can be cited precisely.
    """
    from rag.embeddings import embed_batch  # local import to avoid loading model unless building

    init_schema()

    all_chunks = []
    metadata = []
    for entry in entries:
        for piece in chunk_text(entry["text"]):
            all_chunks.append(piece)
            metadata.append({"source": entry["source"], "page": entry.get("page"), "text": piece})

    if not all_chunks:
        print("No documents or chunks found to index.")
        return

    vectors = embed_batch(all_chunks)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE rag_documents RESTART IDENTITY")
            for meta, vec in zip(metadata, vectors):
                cur.execute(
                    """
                    INSERT INTO rag_documents (source, page, text, embedding)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (meta["source"], meta["page"], meta["text"], vec.tolist()),
                )
        conn.commit()
        sources = {e["source"] for e in entries}
        print(f"Indexed {len(all_chunks)} chunks from {len(sources)} source documents into PostgreSQL pgvector.")
    finally:
        conn.close()


def search(query_vector, top_k: int = 4) -> list[dict]:
    """
    Performs cosine similarity vector search against PostgreSQL rag_documents table.
    """
    conn = get_connection()
    try:
        q_vec = query_vector.tolist() if hasattr(query_vector, "tolist") else list(query_vector)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source, page, text, 1 - (embedding <=> %s::vector) AS score
                FROM rag_documents
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (q_vec, q_vec, top_k),
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append({
                    "source": r["source"],
                    "page": r["page"],
                    "text": r["text"],
                    "score": float(r["score"]),
                })
            return results
    finally:
        conn.close()

