"""
Loads research papers/reports (PDF) into (text, metadata) chunks for the semantic
index. Unlike the hand-written .md documents, PDF chunks carry a page number, so
retrieved evidence can be cited as "Smith et al. 2023, p.14" rather than just a
filename — this is what lets recommendations point at a specific, checkable location
in a real source instead of a vague "FAO guidance" attribution.
"""
import os
from pypdf import PdfReader


def load_pdf(path: str) -> list[dict]:
    """Returns a list of {source, page, text} — one entry per page with real content."""
    reader = PdfReader(path)
    filename = os.path.basename(path)
    entries = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if len(text) < 40:  # skip near-empty pages (figures, blank pages, cover pages)
            continue
        entries.append({"source": filename, "page": page_num, "text": text})
    return entries


def load_all_pdfs(directory: str) -> list[dict]:
    """Loads every PDF in a directory. Missing/unreadable files are reported, not fatal —
    one corrupt PDF shouldn't block indexing the rest of the knowledge base."""
    all_entries = []
    if not os.path.isdir(directory):
        return all_entries
    for fname in os.listdir(directory):
        if not fname.lower().endswith(".pdf"):
            continue
        path = os.path.join(directory, fname)
        try:
            entries = load_pdf(path)
            all_entries.extend(entries)
            print(f"  Loaded {fname}: {len(entries)} pages with content")
        except Exception as e:
            print(f"  WARNING: failed to load {fname}: {e}")
    return all_entries
