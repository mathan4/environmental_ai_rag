"""
Run once (and again any time knowledge/documents/, knowledge/papers/, or
knowledge/datasets/ changes) to build:
1. The FAISS semantic index — from hand-written docs (knowledge/documents/*.md)
   AND real research papers/reports (knowledge/papers/*.pdf), with page-level
   citation tracking for PDFs.
2. The seeded SQLite structured-intervention database (curated benchmarks).
3. Any CSV environmental datasets (knowledge/datasets/*.csv) — loaded as their own
   queryable SQLite tables, registered in `dataset_registry`.

Drop your own PDFs into knowledge/papers/ and CSVs into knowledge/datasets/ before
running this — nothing here is hardcoded to the starter files.
"""
import os
from rag.vector_store import build_index
from db.seed_data import seed
from knowledge.ingestion.pdf_loader import load_all_pdfs
from knowledge.ingestion.csv_loader import load_all_csvs

BASE_DIR = os.path.dirname(__file__)
DOCS_DIR = os.path.join(BASE_DIR, "knowledge", "documents")
PAPERS_DIR = os.path.join(BASE_DIR, "knowledge", "papers")
DATASETS_DIR = os.path.join(BASE_DIR, "knowledge", "datasets")


def load_markdown_entries() -> list[dict]:
    """Hand-written docs become single entries (page=None) -- chunking happens in build_index."""
    entries = []
    if not os.path.isdir(DOCS_DIR):
        return entries
    for fname in os.listdir(DOCS_DIR):
        if fname.endswith(".md"):
            with open(os.path.join(DOCS_DIR, fname), encoding="utf-8") as f:
                entries.append({"source": fname, "page": None, "text": f.read()})
    return entries


if __name__ == "__main__":
    print("Loading hand-written knowledge documents...")
    md_entries = load_markdown_entries()
    print(f"  Found {len(md_entries)} markdown documents.")

    print("\nLoading research papers/reports (PDF)...")
    pdf_entries = load_all_pdfs(PAPERS_DIR)
    if not pdf_entries:
        print(f"  No PDFs found in {PAPERS_DIR} -- add real research papers there and re-run.")

    print("\nBuilding semantic index (markdown + PDFs combined)...")
    build_index(md_entries + pdf_entries)

    print("\nSeeding curated structured intervention benchmarks...")
    seed()

    print("\nLoading structured CSV datasets...")
    tables = load_all_csvs(DATASETS_DIR)
    if not tables:
        print(f"  No CSVs found in {DATASETS_DIR} -- add datasets there and re-run to make them queryable.")

    print("\nKnowledge base build complete.")
