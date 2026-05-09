import os
import io
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class OCRLoader:
    @staticmethod
    def extract_with_ocr(pdf_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        """Fallback OCR extraction for scanned PDFs using pytesseract and pdf2image.
        
        Requires `poppler` and `tesseract-ocr` installed on the system, 
        and `pdf2image`, `pytesseract`, `Pillow` in Python environment.
        """
        if not os.getenv("PDF_OCR_ENABLED", "false").lower() in ("true", "1", "yes"):
            logger.info("OCR is disabled. Skipping OCR extraction for %s", filename)
            return []
            
        try:
            from pdf2image import convert_from_bytes
            import pytesseract
        except ImportError:
            logger.warning("OCR libraries (pdf2image, pytesseract) not installed. Skipping OCR.")
            return []

        logger.info("Starting OCR extraction for %s", filename)
        try:
            images = convert_from_bytes(pdf_bytes)
            pages = []
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image)
                if text.strip():
                    pages.append({
                        "text": text,
                        "metadata": {
                            "page": i + 1,
                            "filename": filename,
                            "source_parser": "ocr",
                        }
                    })
            logger.info("OCR extraction completed for %s with %d pages", filename, len(pages))
            return pages
        except Exception as e:
            logger.error("OCR extraction failed for %s: %s", filename, e)
            return []
