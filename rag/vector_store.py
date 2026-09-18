"""
FAISS-backed vector store for the knowledge documents.

Chosen over a full DB-hosted vector extension deliberately: this system needs no
server to run at all — index + chunk text are saved to disk as plain files and
loaded back in on startup. Simpler to hand off / deploy than a Postgres+pgvector setup.
"""
import os
import pickle
import numpy as np
import faiss

INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge", "index")
INDEX_PATH = os.path.join(INDEX_DIR, "faiss.index")
CHUNKS_PATH = os.path.join(INDEX_DIR, "chunks.pkl")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    """Simple sliding-window chunking by characters (good enough for these doc sizes)."""
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
    resulting chunk keeps its source/page so retrieved evidence can be cited precisely
    (e.g. "IPCC_AR6_WG2.pdf, p.14" for a PDF, vs just a filename for hand-written docs).
    """
    from rag.embeddings import embed_batch  # local import to avoid loading the model unless building

    os.makedirs(INDEX_DIR, exist_ok=True)
    all_chunks = []
    metadata = []
    for entry in entries:
        for piece in chunk_text(entry["text"]):
            all_chunks.append(piece)
            metadata.append({"source": entry["source"], "page": entry.get("page"), "text": piece})

    vectors = np.array(embed_batch(all_chunks)).astype("float32")
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product == cosine similarity since vectors are normalized
    index.add(vectors)

    faiss.write_index(index, INDEX_PATH)
    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(metadata, f)

    sources = {e["source"] for e in entries}
    print(f"Indexed {len(all_chunks)} chunks from {len(sources)} source documents.")


_index = None
_metadata = None


def _load():
    global _index, _metadata
    if _index is None:
        if not os.path.exists(INDEX_PATH):
            raise RuntimeError("No FAISS index found. Run build_knowledge_base.py first.")
        _index = faiss.read_index(INDEX_PATH)
        with open(CHUNKS_PATH, "rb") as f:
            _metadata = pickle.load(f)
    return _index, _metadata


def search(query_vector, top_k: int = 4) -> list[dict]:
    index, metadata = _load()
    q = np.array([query_vector]).astype("float32")
    scores, indices = index.search(q, top_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        results.append({**metadata[idx], "score": float(score)})
    return results
