import os
import io
import base64
import binascii
import hashlib
import logging
import pypdf
from fastapi import UploadFile
from typing import List, Dict, Any
from app.utils.text_normalizer import normalize_extracted_text

logger = logging.getLogger(__name__)

# Maximum upload size — override via MAX_UPLOAD_SIZE_MB env-var (default 50 MB).
_MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50")) * 1024 * 1024

class FileProcessor:
    @staticmethod
    def _coerce_pdf_bytes(pdf_content: Any) -> bytes:
        """Return raw PDF bytes from either bytes, base64-encoded DB content, or file storage sentinel.

        Raises ValueError when content is legacy text-only data rather than
        encoded PDF binary.
        """
        if isinstance(pdf_content, bytes):
            pdf_bytes = pdf_content
        elif isinstance(pdf_content, str):
            if pdf_content.startswith("pdf://"):
                from app.services.file_storage import get_file_storage
                key = pdf_content[len("pdf://"):]
                try:
                    pdf_bytes = get_file_storage().load(key)
                except Exception as exc:
                    raise ValueError(f"Failed to load PDF from storage: {exc}") from exc
            else:
                try:
                    pdf_bytes = base64.b64decode(pdf_content, validate=True)
                except (binascii.Error, ValueError) as exc:
                    raise ValueError("Stored PDF is not base64-encoded binary") from exc
        else:
            raise ValueError("Unsupported PDF content type")

        # Accept whitespace/BOM before header, then verify this is actually PDF data.
        if not pdf_bytes.lstrip().startswith(b"%PDF-"):
            raise ValueError("Stored PDF bytes do not contain a valid PDF header")

        return pdf_bytes

    @staticmethod
    async def process_upload(file: UploadFile) -> dict:
        filename = file.filename
        if not filename:
            raise ValueError("No filename provided")

        # Detect file type from extension
        ext = os.path.splitext(filename)[1].lower()
        file_type = ext.lstrip('.')

        # Read the file bytes
        content_bytes = await file.read()
        file_size = len(content_bytes)

        # --- P1.1: Size guard ------------------------------------------------
        if file_size > _MAX_UPLOAD_BYTES:
            limit_mb = _MAX_UPLOAD_BYTES // (1024 * 1024)
            raise ValueError(
                f"File '{filename}' exceeds the maximum allowed upload size of {limit_mb} MB "
                f"(uploaded: {file_size / (1024 * 1024):.1f} MB). "
                "Increase MAX_UPLOAD_SIZE_MB env-var if needed."
            )

        # --- P1.1: MIME-type + magic-byte validation for PDFs ----------------
        if file_type == "pdf":
            # Magic-byte check — must start with %PDF- (allow leading whitespace/BOM)
            if not content_bytes.lstrip()[:5] == b"%PDF-":
                raise ValueError(
                    f"File '{filename}' does not appear to be a valid PDF "
                    "(missing %PDF- header). Upload rejected."
                )
            # MIME sniff via filetype library (already a project dependency)
            try:
                import filetype as _ft
                kind = _ft.guess(content_bytes)
                if kind is not None and kind.mime not in ("application/pdf",):
                    raise ValueError(
                        f"File '{filename}' MIME type detected as '{kind.mime}', "
                        "expected 'application/pdf'. Upload rejected."
                    )
            except ImportError:
                # filetype not installed — fall back to magic-byte check only
                logger.debug("filetype library not available; skipping MIME sniff for '%s'", filename)

        extracted_text = ""
        stored_content = ""

        # Process based on file extension
        if file_type == 'txt':
            try:
                extracted_text = normalize_extracted_text(content_bytes.decode('utf-8'))
            except UnicodeDecodeError:
                extracted_text = normalize_extracted_text(content_bytes.decode('latin-1', errors='replace'))
            stored_content = extracted_text

        elif file_type == 'pdf':
            # P1.2: Store PDF bytes in FileStorage instead of base64 in DB
            from app.services.file_storage import get_file_storage
            storage = get_file_storage()
            storage_key = storage.save(content_bytes, extension="pdf")
            stored_content = f"pdf://{storage_key}"

            pdf_file = io.BytesIO(content_bytes)
            try:
                pdf_reader = pypdf.PdfReader(pdf_file)
                text_parts = []
                for page in pdf_reader.pages:
                    text = normalize_extracted_text(page.extract_text() or "")
                    if text:
                        text_parts.append(text)
                extracted_text = "\n".join(text_parts)
            except Exception as e:
                # For corrupted PDFs, we fall back to empty text
                # (page extraction will also fail gracefully and fall back to flat)
                import logging
                logging.getLogger(__name__).warning(
                    f"Failed to extract text from PDF '{filename}' during upload: {str(e)}"
                )
                extracted_text = f"[PDF content could not be extracted - {filename}]"

        else:
            raise ValueError(f"Unsupported file type: {ext}. Only .txt and .pdf are supported.")

        return {
            "content": stored_content,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            # P3.2: SHA-256 of raw bytes for content-level deduplication.
            "content_sha256": hashlib.sha256(content_bytes).hexdigest(),
        }

    @staticmethod
    def extract_pdf_pages(pdf_content, filename: str = "document.pdf") -> List[Dict[str, Any]]:
        """Extract pages from PDF with structure preservation.

        Handles both raw PDF bytes and base64-encoded PDF content (from database).

        Each page is returned as a dict with text and metadata, enabling
        per-page chunking and preservation of page boundaries.

        Args:
            pdf_content: Either raw PDF bytes or base64-encoded string (from DB).
            filename: Original filename for metadata.

        Returns:
            List of dicts, each containing:
                - text: Page text content
                - metadata: Dict with page number, filename, etc.

        Raises:
            ValueError: If PDF cannot be parsed.
        """
        from app.services.pdf_loader import PDFStructureLoader

        try:
            pdf_bytes = FileProcessor._coerce_pdf_bytes(pdf_content)
        except ValueError:
            if isinstance(pdf_content, str):
                legacy_text = FileProcessor.extract_pdf_text_fallback(pdf_content, filename)
                if legacy_text:
                    return [
                        {
                            "text": legacy_text,
                            "metadata": {
                                "page_number": 1,
                                "total_pages": 1,
                                "filename": filename,
                                "source_type": "legacy_text",
                            },
                        }
                    ]
            raise

        try:
            pages = PDFStructureLoader.load_from_bytes(pdf_bytes, filename)
            parser_used = "unknown"
            if pages and isinstance(getattr(pages[0], "metadata", None), dict):
                parser_used = pages[0].metadata.get("source_parser", "pypdf")
            logger.info(
                "PDF extraction completed for '%s' using parser=%s with %d page(s)",
                filename,
                parser_used,
                len(pages),
            )
            return [
                {
                    "text": normalize_extracted_text(page.text),
                    "metadata": page.metadata
                }
                for page in pages
            ]
        except ValueError:
            raise

    @staticmethod
    def extract_pdf_text_fallback(pdf_content: Any, filename: str = "document.pdf") -> str:
        """Best-effort text extraction for PDF content used during fallback paths.

        - For valid PDF binary (bytes/base64), extracts text with pypdf.
        - For legacy rows where `content` already contains flattened text,
          returns the string directly.
        """
        if isinstance(pdf_content, str):
            # Legacy DB rows may already contain flattened text rather than PDF bytes.
            if "%PDF-" not in pdf_content[:64]:
                stripped = pdf_content.strip()
                if stripped:
                    return normalize_extracted_text(stripped)

        try:
            pdf_bytes = FileProcessor._coerce_pdf_bytes(pdf_content)
            pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            text_parts: List[str] = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            extracted = normalize_extracted_text("\n".join(text_parts))
            if extracted:
                return extracted
        except Exception:
            pass

        return f"[PDF {filename}: content unavailable]"

    @staticmethod
    def extract_pdf_images(pdf_content: Any, filename: str = "document.pdf") -> List[Any]:
        """Extract embedded PDF images as image chunks.

        The returned chunks use ``image://<storage-key>`` as their text payload
        so a multimodal embedder can load the original image bytes later.
        """
        from app.services.image_loader import PDFImageLoader

        pdf_bytes = FileProcessor._coerce_pdf_bytes(pdf_content)
        min_width = int(os.getenv("PDF_IMAGE_MIN_WIDTH", "64"))
        min_height = int(os.getenv("PDF_IMAGE_MIN_HEIGHT", "64"))
        return PDFImageLoader.extract_from_bytes(
            pdf_bytes=pdf_bytes,
            filename=filename,
            min_width=min_width,
            min_height=min_height,
        )
