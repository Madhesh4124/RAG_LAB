"""PDF table extraction utilities using pdfplumber.

Produces `Chunk` objects (row/table/cell-level) suitable for the
existing chunking -> embedding -> vectorstore pipeline.
"""

from typing import List, Dict, Any, Tuple
import uuid

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore

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
    """Serialize a DataFrame to a clean, well-formatted Markdown table.

    Supports single-row headers as well as two-tier/multi-level headers
    common in scientific benchmark tables (e.g., metric name above CN/EN columns).
    """
    if df.empty:
        return ""

    # Normalize cells: trim, collapse inner whitespaces, escape unescaped pipes
    def _clean_cell(val: Any) -> str:
        if val is None or pd.isna(val):
            return ""
        s = str(val).strip().replace("\r\n", " ").replace("\n", " ")
        s = " ".join(s.split())
        return s.replace("|", "\\|")

    cleaned = df.map(_clean_cell) if hasattr(df, "map") else df.applymap(_clean_cell)

    if len(cleaned) >= 2:
        r0 = list(cleaned.iloc[0])
        r1 = list(cleaned.iloc[1])
        # Check if r0 has spans (empty strings) while r1 provides sub-labels (e.g. CN, EN)
        empty_in_r0 = sum(1 for c in r0 if not c)
        has_subheaders = any(c for c in r1)
        if empty_in_r0 > 0 and has_subheaders:
            # Forward-fill r0
            filled_r0 = []
            current = ""
            for cell in r0:
                if cell:
                    current = cell
                filled_r0.append(current)
            header = []
            for h0, h1 in zip(filled_r0, r1):
                if h0 and h1 and h0.lower() != h1.lower():
                    header.append(f"{h0} {h1}".strip())
                elif h0:
                    header.append(h0)
                elif h1:
                    header.append(h1)
                else:
                    header.append(f"Col_{len(header) + 1}")
            body = cleaned.iloc[2:]
        else:
            header = [c if c else f"Col_{i + 1}" for i, c in enumerate(r0)]
            body = cleaned.iloc[1:]
    else:
        header = [c if c else f"Col_{i + 1}" for i, c in enumerate(cleaned.iloc[0])]
        body = cleaned.iloc[1:]

    # Ensure no empty headers
    header = [h if h.strip() else f"Col_{i + 1}" for i, h in enumerate(header)]

    md = "| " + " | ".join(header) + " |\n"
    md += "| " + " | ".join(["---"] * len(header)) + " |\n"
    for _, row in body.iterrows():
        row_vals = [str(x) for x in row.tolist()]
        if len(row_vals) < len(header):
            row_vals += [""] * (len(header) - len(row_vals))
        elif len(row_vals) > len(header):
            row_vals = row_vals[:len(header)]
        md += "| " + " | ".join(row_vals) + " |\n"
    return md


def _extract_chunks_from_pdfplumber_obj(
    pdf: Any,
    source_name: str,
    chunk_level: str = "table",
    include_header: bool = True,
    context_rows: int = 0,
) -> List[Chunk]:
    chunks: List[Chunk] = []
    table_id_counter = 0

    for page_idx, page in enumerate(pdf.pages):
        tables = page.find_tables() or []

        if not tables:
            raw_tables = page.extract_tables() or []
            for t in raw_tables:
                if not t or len(t) < 2:
                    continue
                df = _df_from_table(t)
                table_id_counter += 1
                meta_base = {
                    "source_file": source_name,
                    "filename": source_name,
                    "page": page.page_number,
                    "page_index": page_idx,
                    "table_id": str(table_id_counter),
                    "modality": "table",
                    "bbox": None,
                }
                if chunk_level == "table":
                    text = _table_to_markdown(df) if include_header else df.to_csv(index=False)
                    chunks.append(Chunk(text=text, metadata={**meta_base, "chunk_level": "table"}, start_char=0, end_char=len(text)))
                elif chunk_level == "row":
                    header = list(df.iloc[0].astype(str)) if include_header and not df.empty else [f"col{i}" for i in range(df.shape[1])]
                    for ridx in range(1 if include_header and not df.empty else 0, len(df)):
                        row_vals = df.iloc[ridx].astype(str).tolist()
                        text = " | ".join([f"{h}: {v}" for h, v in zip(header, row_vals)])
                        meta = {**meta_base, "chunk_level": "row", "row_index": ridx - (1 if include_header and not df.empty else 0), "column_names": header}
                        chunks.append(Chunk(text=text, metadata=meta, start_char=0, end_char=len(text)))
                else:
                    header = list(df.iloc[0].astype(str)) if include_header and not df.empty else [f"col{i}" for i in range(df.shape[1])]
                    for ridx in range(1 if include_header and not df.empty else 0, len(df)):
                        for cidx, val in enumerate(df.iloc[ridx].astype(str).tolist()):
                            text = f"{header[cidx]}: {val}"
                            meta = {**meta_base, "chunk_level": "cell", "row_index": ridx - (1 if include_header and not df.empty else 0), "col_index": cidx, "column_name": header[cidx]}
                            chunks.append(Chunk(text=text, metadata=meta, start_char=0, end_char=len(text)))
            continue

        for t in tables:
            try:
                table_data = t.extract()
            except Exception:
                table_data = None

            if not table_data or len(table_data) < 2:
                continue

            df = _df_from_table(table_data)
            bbox = tuple(t.bbox) if hasattr(t, "bbox") and t.bbox else None
            table_id_counter += 1
            meta_base = {
                "source_file": source_name,
                "filename": source_name,
                "page": page.page_number,
                "page_index": page_idx,
                "table_id": str(table_id_counter),
                "modality": "table",
                "bbox": bbox,
            }

            if chunk_level == "table":
                text = _table_to_markdown(df) if include_header else df.to_csv(index=False)
                chunks.append(Chunk(text=text, metadata={**meta_base, "chunk_level": "table"}, start_char=0, end_char=len(text)))
            elif chunk_level == "row":
                header = list(df.iloc[0].astype(str)) if include_header and not df.empty else [f"col{i}" for i in range(df.shape[1])]
                for ridx in range(1 if include_header and not df.empty else 0, len(df)):
                    row_vals = df.iloc[ridx].astype(str).tolist()
                    start = max(1 if include_header and not df.empty else 0, ridx - context_rows)
                    end = min(len(df), ridx + context_rows + 1)
                    context_rows_text = []
                    for rr in range(start, end):
                        rv = df.iloc[rr].astype(str).tolist()
                        context_rows_text.append(" | ".join([f"{h}: {v}" for h, v in zip(header, rv)]))
                    text = "\n".join(context_rows_text)
                    meta = {**meta_base, "chunk_level": "row", "row_index": ridx - (1 if include_header and not df.empty else 0), "column_names": header}
                    chunks.append(Chunk(text=text, metadata=meta, start_char=0, end_char=len(text)))
            else:
                header = list(df.iloc[0].astype(str)) if include_header and not df.empty else [f"col{i}" for i in range(df.shape[1])]
                for ridx in range(1 if include_header and not df.empty else 0, len(df)):
                    for cidx, val in enumerate(df.iloc[ridx].astype(str).tolist()):
                        text = f"{header[cidx]}: {val}"
                        meta = {**meta_base, "chunk_level": "cell", "row_index": ridx - (1 if include_header and not df.empty else 0), "col_index": cidx, "column_name": header[cidx]}
                        chunks.append(Chunk(text=text, metadata=meta, start_char=0, end_char=len(text)))

    return chunks


def extract_tables_from_file(
    file_path: str,
    chunk_level: str = "table",
    include_header: bool = True,
    context_rows: int = 0,
) -> List[Chunk]:
    """Extract tables from a PDF file path and return a list of `Chunk` objects."""
    if pdfplumber is None:
        return []
    with pdfplumber.open(file_path) as pdf:
        return _extract_chunks_from_pdfplumber_obj(
            pdf=pdf,
            source_name=file_path,
            chunk_level=chunk_level,
            include_header=include_header,
            context_rows=context_rows,
        )


def extract_tables_from_bytes(
    pdf_bytes: bytes,
    filename: str = "document.pdf",
    chunk_level: str = "table",
    include_header: bool = True,
    context_rows: int = 0,
) -> List[Chunk]:
    """Extract tables from PDF bytes and return a list of `Chunk` objects."""
    if pdfplumber is None:
        return []
    import io
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return _extract_chunks_from_pdfplumber_obj(
            pdf=pdf,
            source_name=filename,
            chunk_level=chunk_level,
            include_header=include_header,
            context_rows=context_rows,
        )

