PDF Table Indexing
===================

This directory contains utilities to extract tables from PDFs using `pdfplumber`,
optionally OCR scanned pages via `pytesseract`/`pdf2image`, chunk table content,
embed it, and store embeddings in the project's Chroma vectorstore.

Quickstart
----------

- Index a file into Chroma (row-level chunks by default):

```bash
source .venv/Scripts/activate
python -m backend.scripts.index_tables path/to/document.pdf --collection my_tables
```

Configuration notes
- The OCR fallback is controlled by `PDF_OCR_ENABLED=true` and requires
  system `tesseract` and `poppler` plus the Python packages `pytesseract` and `pdf2image`.
- The script uses the project's `PipelineFactory` to create the embedder and
  vectorstore. Override `embedding_provider`/`embedding_model` in `table_indexer` when needed.

Files
- `app/services/pdf_table_extractor.py`: table detection and conversion helpers.
- `app/services/table_indexer.py`: orchestrator to index extracted table chunks.
- `backend/scripts/index_tables.py`: small CLI helper for local testing.
