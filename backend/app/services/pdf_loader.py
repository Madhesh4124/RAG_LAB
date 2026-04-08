"""
PDF document loader that preserves page-level structure.

Extracts pages as separate structured documents with metadata,
enabling per-page chunking and better context preservation.
"""

import io
import logging
from typing import List, Dict, Any

import pypdf

logger = logging.getLogger(__name__)


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
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            reader = pypdf.PdfReader(pdf_file)
        except Exception as e:
            raise ValueError(f"Failed to parse PDF: {str(e)}")

        pages = []
        total_pages = len(reader.pages)

        for page_num, page_obj in enumerate(reader.pages):
            try:
                text = page_obj.extract_text() or ""
            except Exception as e:
                logger.warning(
                    "Failed to extract text from page %d/%d: %s",
                    page_num + 1,
                    total_pages,
                    str(e),
                )
                text = ""

            # Skip empty pages if requested
            if skip_empty and not text.strip():
                logger.debug(
                    "Skipping empty page %d/%d",
                    page_num + 1,
                    total_pages,
                )
                continue

            # Create page with metadata
            page_metadata = {
                "page": page_num + 1,  # 1-indexed for readability
                "filename": filename,
                "page_0_indexed": page_num,
            }

            page = PDFPage(
                page_num=page_num,
                text=text,
                metadata=page_metadata,
            )
            pages.append(page)

        if not pages:
            raise ValueError("No text extracted from PDF")

        logger.debug(
            "Extracted %d non-empty pages (skipped %d empty) from PDF '%s'",
            len(pages),
            total_pages - len(pages),
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
