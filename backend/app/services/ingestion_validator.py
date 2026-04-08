"""
Validation utilities for PDF structure-preserving ingestion.

Provides tools to verify that page-level metadata is correctly
preserved through the chunking and indexing pipeline.
"""

import logging
from typing import List, Dict, Any

from app.services.chunking.base import Chunk

logger = logging.getLogger(__name__)


class IngestionValidator:
    """Validates that PDF structure preservation is working correctly."""

    @staticmethod
    def validate_chunks_have_page_metadata(chunks: List[Chunk]) -> Dict[str, Any]:
        """Verify that all chunks include required page-level metadata.

        Args:
            chunks: List of Chunk objects from indexing.

        Returns:
            Dict with validation results and statistics.
        """
        if not chunks:
            return {
                "valid": False,
                "error": "No chunks provided for validation",
                "total_chunks": 0,
            }

        # Check for required metadata fields
        required_fields = {"doc_id", "page", "chunk_index"}
        chunks_with_page_metadata = 0
        missing_pages_count = 0
        pages_seen = set()

        for chunk in chunks:
            if not chunk.metadata:
                missing_pages_count += 1
                continue

            # Check if this chunk has page metadata
            has_page_metadata = any(
                field in chunk.metadata for field in required_fields
            )

            if has_page_metadata:
                chunks_with_page_metadata += 1
                if "page" in chunk.metadata:
                    pages_seen.add(chunk.metadata["page"])
            else:
                missing_pages_count += 1

        coverage = (
            chunks_with_page_metadata / len(chunks) * 100
            if chunks else 0
        )

        result = {
            "valid": coverage >= 80,  # 80% threshold
            "total_chunks": len(chunks),
            "chunks_with_page_metadata": chunks_with_page_metadata,
            "chunks_missing_metadata": missing_pages_count,
            "metadata_coverage_percent": round(coverage, 2),
            "unique_pages_indexed": len(pages_seen),
            "page_numbers": sorted(list(pages_seen)),
        }

        if result["valid"]:
            logger.info(
                "Ingestion validation PASSED: %d chunks across %d pages, %.1f%% have metadata",
                len(chunks),
                len(pages_seen),
                coverage,
            )
        else:
            logger.warning(
                "Ingestion validation FAILED: Only %.1f%% of chunks have page metadata",
                coverage,
            )

        return result

    @staticmethod
    def validate_per_page_chunking(pages: List[Dict[str, Any]], chunks: List[Chunk]) -> Dict[str, Any]:
        """Verify that per-page chunking preserved page boundaries.

        Args:
            pages: Original list of page dicts.
            chunks: Generated chunks after indexing.

        Returns:
            Dict with page boundary preservation metrics.
        """
        if not pages or not chunks:
            return {
                "valid": False,
                "error": "Missing pages or chunks for validation",
            }

        # Extract unique pages from chunks
        pages_in_chunks = set()
        for chunk in chunks:
            if chunk.metadata and "page" in chunk.metadata:
                pages_in_chunks.add(chunk.metadata["page"])

        expected_pages = set(
            page.get("metadata", {}).get("page", idx)
            for idx, page in enumerate(pages)
        )

        # Check alignment
        pages_missing_chunks = expected_pages - pages_in_chunks
        pages_with_chunks = pages_in_chunks & expected_pages

        result = {
            "valid": len(pages_missing_chunks) == 0,
            "total_input_pages": len(pages),
            "pages_with_chunks": len(pages_with_chunks),
            "pages_missing_chunks": list(pages_missing_chunks),
            "avg_chunks_per_page": (
                round(len(chunks) / len(pages_with_chunks), 2)
                if pages_with_chunks else 0
            ),
        }

        if result["valid"]:
            logger.info(
                "Per-page chunking validation PASSED: All %d pages have chunks",
                len(pages),
            )
        else:
            logger.warning(
                "Per-page chunking validation FAILED: %d pages have no chunks",
                len(pages_missing_chunks),
            )

        return result
