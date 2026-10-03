"""
PDF document loader that preserves page-level structure.

Extracts pages as separate structured documents with metadata,
enabling per-page chunking and better context preservation.
"""

import io
import json
import logging
import os
import tempfile
from typing import List, Dict, Any
from pathlib import Path

import pypdf

from app.utils.text_normalizer import normalize_extracted_text

logger = logging.getLogger(__name__)


def get_pdf_parser_backend() -> str:
    return os.getenv("PDF_PARSER_BACKEND", "auto").strip().lower()


def get_odl_quiet_mode() -> bool:
    return os.getenv("ODL_QUIET", "1").strip().lower() not in ("0", "false", "no", "off")


def get_pdf_parser_status() -> Dict[str, Any]:
    backend = get_pdf_parser_backend()
    opendataloader_available = True
    try:
        import opendataloader_pdf  # noqa: F401
    except Exception:
        opendataloader_available = False

    return {
        "configured_backend": backend,
        "opendataloader_available": opendataloader_available,
        "fallback_backend": "pypdf",
    }


def _effective_min_total_chars(total_pages: int, min_total_chars: int) -> int:
    """Return the effective min-char threshold used by auto quality checks.

    For very short documents, a fixed global threshold (for example 500 chars)
    can be too strict and trigger unnecessary parser fallback. This scales the
    threshold down for short docs while preserving the existing threshold for
    larger documents.
    """
    short_doc_max_pages = int(os.getenv("PDF_AUTO_SHORT_DOC_MAX_PAGES", "2"))
    short_doc_chars_per_page = int(os.getenv("PDF_AUTO_SHORT_DOC_CHARS_PER_PAGE", "150"))

    if total_pages > 0 and total_pages <= short_doc_max_pages:
        short_doc_threshold = max(1, total_pages) * short_doc_chars_per_page
        return min(min_total_chars, short_doc_threshold)

    return min_total_chars


def _pypdf_text_quality_ok(pages: List["PDFPage"], total_pages: int) -> bool:
    min_pages_ratio = float(os.getenv("PDF_AUTO_MIN_TEXT_PAGE_RATIO", "0.6"))
    min_total_chars = int(os.getenv("PDF_AUTO_MIN_TOTAL_CHARS", "500"))

    non_empty_pages = sum(1 for page in pages if (page.text or "").strip())
    total_chars = sum(len((page.text or "").strip()) for page in pages)
    required_chars = _effective_min_total_chars(total_pages, min_total_chars)

    if total_pages <= 0:
        return total_chars >= required_chars

    return (
        non_empty_pages >= max(1, int(total_pages * min_pages_ratio))
        and total_chars >= required_chars
    )


class PDFPage:
    """Represents a single page extracted from a PDF."""

    def __init__(self, page_num: int, text: str, metadata: Dict[str, Any]):
        """
        Args:
            page_num: Zero-indexed page number.
            text: Extracted text from the page.
            metadata: Additional metadata for this page.
        """
        self.page_num = page_num
        self.text = text
        self.metadata = metadata


class PDFStructureLoader:
    """Loader that extracts PDFs as structured pages with metadata."""

    @staticmethod
    def _normalize_page_number(raw_value: Any) -> int:
        try:
            page_num = int(raw_value)
            return page_num if page_num > 0 else 1
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _extract_elements(payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if not isinstance(payload, dict):
            return []

        for key in ("elements", "data", "result", "kids"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        pages = payload.get("pages")
        if isinstance(pages, list):
            flattened: List[Dict[str, Any]] = []
            for page in pages:
                if not isinstance(page, dict):
                    continue

                page_no = page.get("page number", page.get("page", page.get("page_number", 1)))

                page_elements = page.get("elements")
                if isinstance(page_elements, list):
                    for element in page_elements:
                        if not isinstance(element, dict):
                            continue
                        if "page number" not in element:
                            element = {**element, "page number": page_no}
                        flattened.append(element)
                    continue

                content = page.get("content") or page.get("text")
                if content:
                    flattened.append(
                        {
                            "type": page.get("type", "paragraph"),
                            "page number": page_no,
                            "content": str(content),
                        }
                    )

            return flattened

        return []

    @staticmethod
    def _load_with_opendataloader(
        pdf_bytes: bytes,
        filename: str,
        skip_empty: bool,
    ) -> List[PDFPage]:
        import concurrent.futures
        import shutil
        import opendataloader_pdf

        _ODL_TIMEOUT = int(os.getenv("ODL_TIMEOUT_SECONDS", "120"))

        with tempfile.TemporaryDirectory(prefix="odl_pdf_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            safe_name = Path(filename).name or "document.pdf"
            input_file = tmp_path / safe_name
            output_dir = tmp_path / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            input_file.write_bytes(pdf_bytes)

            # --- P2.5: Enforce a hard timeout on the conversion subprocess ---
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    fut = executor.submit(
                        opendataloader_pdf.convert,
                        input_path=[str(input_file)],
                        output_dir=str(output_dir),
                        format="json",
                        quiet=get_odl_quiet_mode(),
                    )
                    try:
                        fut.result(timeout=_ODL_TIMEOUT)
                    except concurrent.futures.TimeoutError:
                        raise ValueError(
                            f"OpenDataLoader conversion timed out after {_ODL_TIMEOUT} s "
                            f"for '{filename}'. Increase ODL_TIMEOUT_SECONDS env-var if needed."
                        )
            finally:
                # Belt-and-suspenders cleanup: remove any leftover temp files even if
                # a child process crashed without releasing its handles.
                shutil.rmtree(tmp_dir, ignore_errors=True)
            # ------------------------------------------------------------------

            json_files = sorted(output_dir.rglob("*.json"))
            if not json_files:
                raise ValueError("OpenDataLoader did not produce JSON output")

            payload = json.loads(json_files[0].read_text(encoding="utf-8"))

        elements = PDFStructureLoader._extract_elements(payload)
        if not elements:
            raise ValueError("OpenDataLoader JSON contains no extractable elements")

        page_text_map: Dict[int, List[str]] = {}
        page_element_count: Dict[int, int] = {}

        for element in elements:
            page_num = PDFStructureLoader._normalize_page_number(
                element.get("page number", element.get("page", element.get("page_number", 1)))
            )
            content = str(element.get("content") or element.get("text") or "").strip()

            page_element_count[page_num] = page_element_count.get(page_num, 0) + 1

            if content:
                if page_num not in page_text_map:
                    page_text_map[page_num] = []
                page_text_map[page_num].append(content)

        pages: List[PDFPage] = []
        for page_num in sorted(page_element_count.keys()):
            text = normalize_extracted_text("\n".join(page_text_map.get(page_num, [])))

            if skip_empty and not text.strip():
                continue

            pages.append(
                PDFPage(
                    page_num=page_num - 1,
                    text=text,
                    metadata={
                        "page": page_num,
                        "filename": filename,
                        "page_0_indexed": page_num - 1,
                        "source_parser": "opendataloader_pdf",
                        "element_count": page_element_count.get(page_num, 0),
                    },
                )
            )

        if not pages:
            raise ValueError("No text extracted from OpenDataLoader output")

        return pages

    @staticmethod
    def _load_with_pypdf(
        pdf_bytes: bytes,
        filename: str,
        skip_empty: bool,
    ) -> tuple[List[PDFPage], int]:
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            reader = pypdf.PdfReader(pdf_file)
        except Exception as e:
            raise ValueError(f"Failed to parse PDF: {str(e)}")

        pages = []
        total_pages = len(reader.pages)

        for page_num, page_obj in enumerate(reader.pages):
            try:
                text = normalize_extracted_text(page_obj.extract_text() or "")
            except Exception as e:
                logger.warning(
                    "Failed to extract text from page %d/%d: %s",
                    page_num + 1,
                    total_pages,
                    str(e),
                )
                text = ""

            if skip_empty and not text.strip():
                logger.debug(
                    "Skipping empty page %d/%d",
                    page_num + 1,
                    total_pages,
                )
                continue

            page_metadata = {
                "page": page_num + 1,
                "filename": filename,
                "page_0_indexed": page_num,
                "source_parser": "pypdf",
            }

            pages.append(
                PDFPage(
                    page_num=page_num,
                    text=text,
                    metadata=page_metadata,
                )
            )

        return pages, total_pages

    @staticmethod
    def _load_with_pdfplumber(
        pdf_bytes: bytes,
        filename: str,
        skip_empty: bool,
    ) -> tuple[List[PDFPage], int]:
        import pdfplumber
        from app.services.pdf_table_extractor import _df_from_table, _table_to_markdown

        pages: List[PDFPage] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            for page_idx, page in enumerate(pdf.pages):
                page_num = page_idx + 1

                # 1. Detect and extract structured tables
                tables = []
                try:
                    tables = page.find_tables() or []
                except Exception as e:
                    logger.debug("Table search error on page %d of '%s': %s", page_num, filename, e)

                extracted_tables_md: List[str] = []
                table_bboxes = []
                for t in tables:
                    try:
                        table_data = t.extract()
                        if table_data and len(table_data) >= 2:
                            df = _df_from_table(table_data)
                            md = _table_to_markdown(df)
                            if md.strip():
                                extracted_tables_md.append(md.strip())
                                if hasattr(t, "bbox") and t.bbox:
                                    table_bboxes.append(t.bbox)
                    except Exception as exc:
                        logger.debug("Table extract error on page %d of '%s': %s", page_num, filename, exc)

                # Fallback: if find_tables found nothing, try extract_tables
                if not extracted_tables_md:
                    try:
                        raw_tables = page.extract_tables() or []
                        for t in raw_tables:
                            if t and len(t) >= 2:
                                df = _df_from_table(t)
                                md = _table_to_markdown(df)
                                if md.strip():
                                    extracted_tables_md.append(md.strip())
                    except Exception:
                        pass

                # 2. Extract non-table text
                if table_bboxes:
                    def _not_in_tables(obj: Dict[str, Any]) -> bool:
                        x0 = obj.get("x0", 0)
                        x1 = obj.get("x1", 0)
                        top = obj.get("top", 0)
                        bottom = obj.get("bottom", 0)
                        for bbox in table_bboxes:
                            if (x0 >= bbox[0] - 2 and x1 <= bbox[2] + 2 and
                                top >= bbox[1] - 2 and bottom <= bbox[3] + 2):
                                return False
                        return True

                    try:
                        clean_page = page.filter(_not_in_tables)
                        page_text = clean_page.extract_text() or ""
                    except Exception:
                        page_text = page.extract_text() or ""
                else:
                    page_text = page.extract_text() or ""

                # 3. Assemble full page text with clean Markdown tables
                parts: List[str] = []
                if page_text.strip():
                    parts.append(page_text.strip())
                for t_idx, t_md in enumerate(extracted_tables_md, start=1):
                    parts.append(f"\n\n[Table {t_idx} on Page {page_num}]\n{t_md}\n")

                full_text = normalize_extracted_text("\n".join(parts))

                if skip_empty and not full_text.strip():
                    continue

                page_metadata = {
                    "page": page_num,
                    "filename": filename,
                    "page_0_indexed": page_idx,
                    "source_parser": "pdfplumber",
                    "tables_detected": len(extracted_tables_md),
                }

                pages.append(
                    PDFPage(
                        page_num=page_idx,
                        text=full_text,
                        metadata=page_metadata,
                    )
                )

        return pages, total_pages

    @staticmethod
    def load_from_bytes(
        pdf_bytes: bytes,
        filename: str = "document.pdf",
        skip_empty: bool = True,
    ) -> List[PDFPage]:
        """Extract pages from PDF bytes with structure preservation.

        Args:
            pdf_bytes: Raw PDF file bytes.
            filename: Original filename for metadata.
            skip_empty: Skip pages with no text content.

        Returns:
            List of PDFPage objects, one per page.

        Raises:
            ValueError: If PDF cannot be parsed.
        """
        backend = get_pdf_parser_backend()
        pages: List[PDFPage] = []
        total_pages = 0

        if backend == "pypdf":
            pages, total_pages = PDFStructureLoader._load_with_pypdf(pdf_bytes, filename, skip_empty)
        elif backend == "opendataloader":
            try:
                pages = PDFStructureLoader._load_with_opendataloader(pdf_bytes, filename, skip_empty)
                total_pages = len(pages)
            except ImportError:
                logger.info("opendataloader-pdf is not installed; falling back to pypdf")
                pages, total_pages = PDFStructureLoader._load_with_pypdf(pdf_bytes, filename, skip_empty)
            except Exception as e:
                logger.warning(
                    "OpenDataLoader parsing failed for '%s', falling back to pypdf: %s",
                    filename,
                    str(e),
                )
                pages, total_pages = PDFStructureLoader._load_with_pypdf(pdf_bytes, filename, skip_empty)
        else:
            # "auto" or "pdfplumber": prefer pdfplumber for table & layout preservation
            try:
                pages, total_pages = PDFStructureLoader._load_with_pdfplumber(pdf_bytes, filename, skip_empty)
                logger.info("PDF '%s' loaded via pdfplumber (%d pages, tables preserved)", filename, len(pages))
            except ImportError:
                logger.info("pdfplumber is not installed; falling back to pypdf")
                pages, total_pages = PDFStructureLoader._load_with_pypdf(pdf_bytes, filename, skip_empty)
            except Exception as e:
                logger.warning("pdfplumber failed for '%s', falling back to pypdf: %s", filename, e)
                pages, total_pages = PDFStructureLoader._load_with_pypdf(pdf_bytes, filename, skip_empty)
            if not _pypdf_text_quality_ok(pages, total_pages):
                try:
                    odl_pages = PDFStructureLoader._load_with_opendataloader(pdf_bytes, filename, skip_empty)
                    if odl_pages:
                        pages = odl_pages
                        total_pages = max(total_pages, len(odl_pages))
                        logger.info(
                            "PDF '%s' used OpenDataLoader fallback after weak pypdf extraction",
                            filename,
                        )
                except ImportError:
                    logger.info("opendataloader-pdf is not installed; keeping pypdf result")
                except Exception as e:
                    logger.warning(
                        "OpenDataLoader fallback failed for '%s'; keeping pypdf result: %s",
                        filename,
                        str(e),
                    )

        # P3.1: OCR Fallback if <50% of pages yielded text
        if total_pages > 0 and (len(pages) < total_pages / 2):
            logger.info("PDF %s yielded %d/%d text pages. Attempting OCR fallback.", filename, len(pages), total_pages)
            from app.services.ocr_loader import OCRLoader
            ocr_pages_data = OCRLoader.extract_with_ocr(pdf_bytes, filename)
            if ocr_pages_data:
                # Replace with OCR results if successful
                pages = []
                for p_data in ocr_pages_data:
                    pages.append(PDFPage(
                        page_num=p_data["metadata"]["page"] - 1,
                        text=p_data["text"],
                        metadata=p_data["metadata"]
                    ))

        if not pages:
            raise ValueError("No text extracted from PDF, and OCR was unavailable or failed.")

        logger.debug(
            "Extracted %d non-empty pages from PDF '%s'",
            len(pages),
            filename,
        )

        return pages

    @staticmethod
    def load_from_file(
        file_path: str,
        skip_empty: bool = True,
    ) -> List[PDFPage]:
        """Extract pages from a PDF file path.

        Args:
            file_path: Path to the PDF file.
            skip_empty: Skip pages with no text content.

        Returns:
            List of PDFPage objects.

        Raises:
            ValueError: If file cannot be read or parsed.
        """
        try:
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()
        except Exception as e:
            raise ValueError(f"Failed to read PDF file: {str(e)}")

        return PDFStructureLoader.load_from_bytes(
            pdf_bytes,
            filename=file_path,
            skip_empty=skip_empty,
        )
