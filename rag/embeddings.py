"""Local embedding model — a small (~90MB) sentence-transformer, not a generative LLM."""
from functools import lru_cache
from sentence_transformers import SentenceTransformer

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"  # 384-dim, CPU-friendly


@lru_cache(maxsize=1)
def _model():
    return SentenceTransformer(EMBED_MODEL_NAME)


def embed_text(text: str):
    return _model().encode(text, normalize_embeddings=True)


def embed_batch(texts: list[str]):
    return _model().encode(texts, normalize_embeddings=True)
