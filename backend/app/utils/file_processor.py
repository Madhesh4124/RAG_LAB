import os
import io
import base64
import binascii
import pypdf
from fastapi import UploadFile
from typing import List, Dict, Any

class FileProcessor:
    @staticmethod
    def _coerce_pdf_bytes(pdf_content: Any) -> bytes:
        """Return raw PDF bytes from either bytes or base64-encoded DB content.

        Raises ValueError when content is legacy text-only data rather than
        encoded PDF binary.
        """
        if isinstance(pdf_content, bytes):
            pdf_bytes = pdf_content
        elif isinstance(pdf_content, str):
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
        
        extracted_text = ""
        stored_content = ""
        
        # Process based on file extension
        if file_type == 'txt':
            try:
                extracted_text = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                extracted_text = content_bytes.decode('latin-1', errors='replace')
            stored_content = extracted_text
                
        elif file_type == 'pdf':
            # For PDFs: store base64-encoded binary + extract text for flat fallback
            stored_content = base64.b64encode(content_bytes).decode('utf-8')
            pdf_file = io.BytesIO(content_bytes)
            try:
                pdf_reader = pypdf.PdfReader(pdf_file)
                text_parts = []
                for page in pdf_reader.pages:
                    text = page.extract_text()
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
            "file_size": file_size
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
            return [
                {
                    "text": page.text,
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
                    return stripped

        try:
            pdf_bytes = FileProcessor._coerce_pdf_bytes(pdf_content)
            pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            text_parts: List[str] = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            extracted = "\n".join(text_parts).strip()
            if extracted:
                return extracted
        except Exception:
            pass

        return f"[PDF {filename}: content unavailable]"
