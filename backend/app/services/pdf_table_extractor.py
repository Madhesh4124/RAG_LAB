"""PDF table extraction utilities using pdfplumber.

Produces `Chunk` objects (row/table/cell-level) suitable for the
existing chunking -> embedding -> vectorstore pipeline.
"""

from typing import List, Dict, Any, Tuple
import uuid

import pdfplumber
import pandas as pd

from app.services.chunking.base import Chunk


def _df_from_table(table: List[List[Any]]) -> pd.DataFrame:
    # Replace None with empty string and normalize
    normalized = [[("" if c is None else str(c)).strip() for c in row] for row in table]
    # Ensure rectangular shape
    max_cols = max(len(r) for r in normalized) if normalized else 0
    rows = [r + [""] * (max_cols - len(r)) for r in normalized]
    # Normalize column names to simple indices for downstream clarity
    df = pd.DataFrame(rows)
    return df


def _table_to_markdown(df: pd.DataFrame) -> str:
    # Simple markdown serialization for readability
    if df.empty:
        return ""
    # If first row looks like header, promote it
    header = list(df.iloc[0].astype(str))
    body = df.iloc[1:]
    md = "| " + " | ".join(header) + " |\n"
    md += "| " + " | ".join(["---"] * len(header)) + " |\n"
    for _, row in body.iterrows():
        md += "| " + " | ".join([str(x) for x in row.tolist()]) + " |\n"
    return md


def extract_tables_from_file(
    file_path: str,
    chunk_level: str = "row",
    include_header: bool = True,
    context_rows: int = 0,
) -> List[Chunk]:
    """Extract tables from a PDF file and return a list of `Chunk` objects.

    Args:
        file_path: Path to the PDF file.
        chunk_level: One of 'table', 'row', or 'cell'.
        include_header: When chunking rows/cells, include header row values.
        context_rows: Number of adjacent rows to include around a row chunk.

    Returns:
        List[Chunk]
    """
    chunks: List[Chunk] = []
    table_id_counter = 0

    with pdfplumber.open(file_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            # Prefer structured tables with bounding boxes
            tables = page.find_tables() or []

            # Fallback to extract_tables (less structural info)
            if not tables:
                raw_tables = page.extract_tables()
                # Convert to objects with minimal bbox info
                for t in raw_tables:
                    df = _df_from_table(t)
                    bbox = None
                    table_id_counter += 1
                    meta_base = {
                        "source_file": file_path,
                        "page": page.page_number,
                        "page_index": page_idx,
                        "table_id": str(table_id_counter),
                        "bbox": bbox,
                    }

                    if chunk_level == "table":
                        text = _table_to_markdown(df) if include_header else df.to_csv(index=False)
                        chunks.append(Chunk(text=text, metadata={**meta_base, "chunk_level": "table"}, start_char=0, end_char=len(text)))
                    elif chunk_level == "row":
                        # treat first row as header if requested
                        header = list(df.iloc[0].astype(str)) if include_header and not df.empty else [f"col{i}" for i in range(df.shape[1])]
                        for ridx in range(1 if include_header and not df.empty else 0, len(df)):
                            row_vals = df.iloc[ridx].astype(str).tolist()
                            text = " | ".join([f"{h}: {v}" for h, v in zip(header, row_vals)])
                            meta = {**meta_base, "chunk_level": "row", "row_index": ridx - (1 if include_header and not df.empty else 0), "column_names": header}
                            chunks.append(Chunk(text=text, metadata=meta, start_char=0, end_char=len(text)))
                    else:  # cell-level
                        header = list(df.iloc[0].astype(str)) if include_header and not df.empty else [f"col{i}" for i in range(df.shape[1])]
                        for ridx in range(1 if include_header and not df.empty else 0, len(df)):
                            for cidx, val in enumerate(df.iloc[ridx].astype(str).tolist()):
                                text = f"{header[cidx]}: {val}"
                                meta = {**meta_base, "chunk_level": "cell", "row_index": ridx - (1 if include_header and not df.empty else 0), "col_index": cidx, "column_name": header[cidx]}
                                chunks.append(Chunk(text=text, metadata=meta, start_char=0, end_char=len(text)))

                continue

            # Handle pdfplumber Table objects
            for t in tables:
                try:
                    table_data = t.extract()
                except Exception:
                    table_data = t.extract()

                df = _df_from_table(table_data)
                bbox = tuple(t.bbox) if hasattr(t, "bbox") else None
                table_id_counter += 1
                meta_base = {
                    "source_file": file_path,
                    "page": page.page_number,
                    "page_index": page_idx,
                    "table_id": str(table_id_counter),
                    "bbox": bbox,
                }

                if chunk_level == "table":
                    text = _table_to_markdown(df) if include_header else df.to_csv(index=False)
                    chunks.append(Chunk(text=text, metadata={**meta_base, "chunk_level": "table"}, start_char=0, end_char=len(text)))
                elif chunk_level == "row":
                    header = list(df.iloc[0].astype(str)) if include_header and not df.empty else [f"col{i}" for i in range(df.shape[1])]
                    for ridx in range(1 if include_header and not df.empty else 0, len(df)):
                        row_vals = df.iloc[ridx].astype(str).tolist()
                        # include context rows if requested
                        start = max(1 if include_header and not df.empty else 0, ridx - context_rows)
                        end = min(len(df), ridx + context_rows + 1)
                        context_rows_text = []
                        for rr in range(start, end):
                            rv = df.iloc[rr].astype(str).tolist()
                            context_rows_text.append(" | ".join([f"{h}: {v}" for h, v in zip(header, rv)]))
                        text = "\n".join(context_rows_text)
                        meta = {**meta_base, "chunk_level": "row", "row_index": ridx - (1 if include_header and not df.empty else 0), "column_names": header}
                        chunks.append(Chunk(text=text, metadata=meta, start_char=0, end_char=len(text)))
                else:  # cell-level
                    header = list(df.iloc[0].astype(str)) if include_header and not df.empty else [f"col{i}" for i in range(df.shape[1])]
                    for ridx in range(1 if include_header and not df.empty else 0, len(df)):
                        for cidx, val in enumerate(df.iloc[ridx].astype(str).tolist()):
                            text = f"{header[cidx]}: {val}"
                            meta = {**meta_base, "chunk_level": "cell", "row_index": ridx - (1 if include_header and not df.empty else 0), "col_index": cidx, "column_name": header[cidx]}
                            chunks.append(Chunk(text=text, metadata=meta, start_char=0, end_char=len(text)))

    return chunks
