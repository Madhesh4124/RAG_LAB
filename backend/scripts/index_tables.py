"""Small CLI to index tables from a PDF into Chroma for local testing.

Usage:
    python -m backend.scripts.index_tables path/to/doc.pdf --collection my_tables
"""

import argparse
import logging
import sys

from app.services.table_indexer import index_pdf_tables


def main(argv=None):
    parser = argparse.ArgumentParser(description="Index PDF tables into Chroma")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--collection", default="tables_collection", help="Chroma collection name")
    parser.add_argument("--level", choices=["table", "row", "cell"], default="row", help="Chunk level")
    parser.add_argument("--no-header", action="store_true", help="Don't treat first row as header")
    parser.add_argument("--context", type=int, default=0, help="Context rows to include around a row")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    count = index_pdf_tables(
        file_path=args.pdf,
        collection_name=args.collection,
        chunk_level=args.level,
        include_header=not args.no_header,
        context_rows=args.context,
    )

    print(f"Indexed {count} chunks into collection '{args.collection}'")


if __name__ == "__main__":
    main()
