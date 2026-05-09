"""PDF image extraction utilities.

Images are extracted as binary assets, saved through the configured file
storage backend, and represented as Chunk objects whose text is an image URI.
The image URI can be consumed by a multimodal embedder such as CLIP.
"""

from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path
from typing import Any, Dict, List

import pypdf
from PIL import Image

from app.services.chunking.base import Chunk
from app.services.file_storage import get_file_storage

logger = logging.getLogger(__name__)


class PDFImageLoader:
    """Extract embedded images from PDF bytes."""

    @staticmethod
    def extract_from_bytes(
        pdf_bytes: bytes,
        filename: str,
        min_width: int = 64,
        min_height: int = 64,
    ) -> List[Chunk]:
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except Exception as exc:
            raise ValueError(f"Failed to parse PDF images: {exc}") from exc

        storage = get_file_storage()
        chunks: List[Chunk] = []

        for page_idx, page in enumerate(reader.pages):
            try:
                page_images = list(getattr(page, "images", []) or [])
            except Exception as exc:
                logger.warning(
                    "Failed to inspect images on page %d of '%s': %s",
                    page_idx + 1,
                    filename,
                    exc,
                )
                continue

            for image_idx, image_obj in enumerate(page_images):
                try:
                    image_bytes = bytes(image_obj.data)
                except Exception as exc:
                    logger.warning(
                        "Failed to read image %d on page %d of '%s': %s",
                        image_idx + 1,
                        page_idx + 1,
                        filename,
                        exc,
                    )
                    continue

                image_meta = PDFImageLoader._inspect_image(image_bytes)
                if not image_meta:
                    continue

                width = int(image_meta["width"])
                height = int(image_meta["height"])
                if width < min_width or height < min_height:
                    logger.debug(
                        "Skipping tiny image %d on page %d of '%s' (%dx%d)",
                        image_idx + 1,
                        page_idx + 1,
                        filename,
                        width,
                        height,
                    )
                    continue

                extension = PDFImageLoader._resolve_extension(image_obj, image_meta)
                storage_key = storage.save(image_bytes, extension=extension)
                digest = hashlib.sha256(image_bytes).hexdigest()

                metadata: Dict[str, Any] = {
                    "filename": filename,
                    "file_type": "pdf",
                    "modality": "image",
                    "page": page_idx + 1,
                    "page_0_indexed": page_idx,
                    "image_index_on_page": image_idx,
                    "image_storage_key": storage_key,
                    "image_name": getattr(image_obj, "name", f"image_{image_idx + 1}"),
                    "image_width": width,
                    "image_height": height,
                    "image_format": image_meta.get("format"),
                    "content_hash": digest,
                    "source_parser": "pypdf_image",
                }

                chunks.append(
                    Chunk(
                        text=f"image://{storage_key}",
                        metadata=metadata,
                        start_char=0,
                        end_char=0,
                    )
                )

        logger.info("Extracted %d image chunk(s) from PDF '%s'", len(chunks), filename)
        return chunks

    @staticmethod
    def _inspect_image(image_bytes: bytes) -> Dict[str, Any] | None:
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                return {
                    "width": image.width,
                    "height": image.height,
                    "format": (image.format or "bin").lower(),
                }
        except Exception:
            return None

    @staticmethod
    def _resolve_extension(image_obj: Any, image_meta: Dict[str, Any]) -> str:
        name = str(getattr(image_obj, "name", "") or "")
        suffix = Path(name).suffix.lower().lstrip(".")
        if suffix:
            return suffix

        fmt = str(image_meta.get("format") or "").lower()
        if fmt in {"jpeg", "jpg"}:
            return "jpg"
        if fmt in {"png", "webp", "gif", "bmp", "tiff"}:
            return fmt
        return "bin"
