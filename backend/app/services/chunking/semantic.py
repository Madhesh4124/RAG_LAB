"""
Semantic chunking strategy.

Splits text at natural sentence boundaries (periods, newlines) and
groups sentences together until a size threshold is reached, then
starts a new chunk.
"""

import logging
import re
import uuid
from math import sqrt
from typing import Any, Dict, List, Optional, Tuple

from app.services.chunking.base import BaseChunker, Chunk
from app.services.embedding.base import BaseEmbedder

# Regex that splits on sentence-ending punctuation (.!?) followed by
# whitespace, or on newline characters — while keeping the delimiter
# attached to the preceding sentence.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

logger = logging.getLogger(__name__)


class SemanticChunker(BaseChunker):
    """Chunker that splits text using semantic coherence.

    The chunker first segments text into sentences, embeds them once,
    then grows a chunk while monitoring both size and semantic drift.
    Drift is measured either against the previous sentence or against
    the current chunk centroid embedding.

    Args:
        max_chunk_size: Maximum number of characters allowed in a chunk.
        embedder: Embedding backend used for semantic similarity.
        similarity_threshold: Primary semantic split threshold.
        min_chunk_size: Minimum chunk size before allowing soft splits.
        use_centroid: Compare against chunk centroid when True.
        overlap_sentences: Number of trailing sentences to overlap.
        hard_split_threshold: Forced semantic split threshold.
        smoothing_margin: Margin reducing noisy near-threshold splits.
        debug: Enables split-decision debug logs.
        require_embedder: Raise when embedder is missing.

    Raises:
        ValueError: On invalid configuration values.
    """

    def __init__(
        self,
        max_chunk_size: int = 512,
        embedder: Optional[BaseEmbedder] = None,
        similarity_threshold: float = 0.6,
        min_chunk_size: int = 100,
        use_centroid: bool = True,
        overlap_sentences: int = 0,
        hard_split_threshold: Optional[float] = 0.4,
        max_sentences_per_chunk: Optional[int] = None,
        smoothing_margin: float = 0.05,
        debug: bool = False,
        require_embedder: bool = True,
    ) -> None:
        if max_chunk_size <= 0:
            raise ValueError(
                f"max_chunk_size must be a positive integer, got {max_chunk_size}"
            )
        if min_chunk_size < 0:
            raise ValueError(
                f"min_chunk_size must be >= 0, got {min_chunk_size}"
            )
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(
                "similarity_threshold must be between 0.0 and 1.0"
            )
        if hard_split_threshold is not None and not 0.0 <= hard_split_threshold <= 1.0:
            raise ValueError(
                "hard_split_threshold must be between 0.0 and 1.0 when provided"
            )
        if overlap_sentences < 0:
            raise ValueError(
                f"overlap_sentences must be >= 0, got {overlap_sentences}"
            )
        if max_sentences_per_chunk is not None and max_sentences_per_chunk <= 0:
            raise ValueError(
                "max_sentences_per_chunk must be > 0 when provided"
            )
        if smoothing_margin < 0.0:
            raise ValueError(
                f"smoothing_margin must be >= 0.0, got {smoothing_margin}"
            )

        self.max_chunk_size = max_chunk_size
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.use_centroid = use_centroid
        self.overlap_sentences = overlap_sentences
        self.hard_split_threshold = hard_split_threshold
        self.max_sentences_per_chunk = max_sentences_per_chunk
        self.smoothing_margin = smoothing_margin
        self.debug = debug
        self.require_embedder = require_embedder

        if self.embedder is None and self.require_embedder:
            raise ValueError(
                "SemanticChunker requires an embedder. Provide embedder in pipeline config."
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split *text* into sentence-level segments.

        Splits on sentence-ending punctuation (.!?) followed by
        whitespace, as well as newline characters.  Empty segments
        are discarded.

        Returns:
            A list of non-empty sentence strings.
        """
        segments = _SENTENCE_SPLIT_RE.split(text)
        return [s for s in segments if s.strip()]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sqrt(sum(x * x for x in a))
        norm_b = sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _compute_centroid(vectors: List[List[float]]) -> List[float]:
        """Compute the centroid (mean vector) of a list of vectors."""
        if not vectors:
            return []
        dim = len(vectors[0])
        if dim == 0:
            return []
        if any(len(vector) != dim for vector in vectors):
            return []
        sums = [0.0] * dim
        for vector in vectors:
            for i, value in enumerate(vector):
                sums[i] += value
        count = float(len(vectors))
        return [value / count for value in sums]

    @staticmethod
    def _update_centroid(
        prev_centroid: List[float],
        prev_count: int,
        new_vector: List[float],
    ) -> List[float]:
        """Incrementally update centroid using a new vector."""
        if prev_count < 0:
            return []
        if prev_count == 0:
            return new_vector.copy()
        if not prev_centroid or len(prev_centroid) != len(new_vector):
            return []
        denom = float(prev_count + 1)
        return [
            (prev_centroid[i] * prev_count + new_vector[i]) / denom
            for i in range(len(new_vector))
        ]

    def _build_running_centroid(
        self,
        embeddings: List[List[float]],
        start_idx: int,
        end_idx: int,
    ) -> Tuple[Optional[List[float]], int]:
        """Build a centroid incrementally for embeddings[start_idx:end_idx+1]."""
        if start_idx > end_idx:
            return None, 0

        centroid: Optional[List[float]] = None
        count = 0
        for idx in range(start_idx, end_idx + 1):
            vector = embeddings[idx]
            if centroid is None:
                centroid = vector.copy()
                count = 1
                continue

            updated = self._update_centroid(centroid, count, vector)
            if not updated:
                return None, 0
            centroid = updated
            count += 1

        return centroid, count

    @staticmethod
    def _locate_sentences(text: str, sentences: List[str]) -> List[Tuple[int, int]]:
        """Locate sentence start/end offsets in order within the original text."""
        spans: List[Tuple[int, int]] = []
        cursor = 0
        for sentence in sentences:
            start = text.find(sentence, cursor)
            if start == -1:
                start = text.find(sentence)
                if start == -1:
                    continue
            end = start + len(sentence)
            spans.append((start, end))
            cursor = end
        return spans

    @staticmethod
    def _chunk_text(sentences: List[str], start_idx: int, end_idx: int) -> str:
        return " ".join(sentences[start_idx : end_idx + 1])

    @staticmethod
    def _chunk_char_length(sentences: List[str], start_idx: int, end_idx: int) -> int:
        if end_idx < start_idx:
            return 0
        length = 0
        for idx in range(start_idx, end_idx + 1):
            length += len(sentences[idx])
            if idx > start_idx:
                length += 1
        return length

    def _should_split(
        self,
        current_chunk_len: int,
        similarity: Optional[float],
        split_for_size: bool,
        split_for_span: bool,
    ) -> Tuple[bool, str]:
        """Decide whether to split and return reason for observability/debugging."""
        current_too_small = current_chunk_len < self.min_chunk_size

        hard_split = False
        soft_semantic_split = False
        if similarity is not None:
            if self.hard_split_threshold is not None:
                hard_split = similarity < self.hard_split_threshold
            soft_semantic_split = similarity < (self.similarity_threshold - self.smoothing_margin)

        # Priority 1: hard semantic split.
        if hard_split:
            return True, "hard_semantic"

        # Priority 2: soft semantic split (if min chunk size already satisfied).
        if soft_semantic_split:
            if current_too_small:
                return False, "hold_min_chunk_size"
            return True, "semantic"

        # Priority 3: maximum sentence span cap.
        if split_for_span:
            if current_too_small:
                return False, "hold_min_chunk_size"
            return True, "max_sentences"

        # Priority 4: size-based split.
        if split_for_size:
            return True, "size"

        return False, "continue"

    # ------------------------------------------------------------------
    # BaseChunker interface
    # ------------------------------------------------------------------

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """Split *text* into semantically coherent chunks.

        Splits are triggered by semantic drift and/or size pressure,
        while respecting `min_chunk_size` unless hard semantic drift is
        detected.

        Args:
            text: The full text to be chunked.
            metadata: A dictionary of metadata to attach to each
                      generated chunk.

        Returns:
            A list of Chunk objects.  Returns an empty list when
            *text* is empty.
        """
        if not text:
            return []

        sentences = self._split_sentences(text)
        if not sentences:
            return []

        spans = self._locate_sentences(text, sentences)
        if len(spans) != len(sentences):
            # Safety fallback when offsets cannot be recovered reliably.
            spans = []
            cursor = 0
            for sentence in sentences:
                start = text.find(sentence, cursor)
                if start == -1:
                    start = max(0, cursor)
                end = min(len(text), start + len(sentence))
                spans.append((start, end))
                cursor = end

        if self.embedder is None:
            if self.require_embedder:
                raise ValueError(
                    "SemanticChunker requires an embedder. Provide embedder in pipeline config."
                )
            logger.warning(
                "SemanticChunker running without embedder; using size/span-only splitting."
            )
            embeddings = None
        else:
            embeddings = self.embedder.embed_batch(sentences)

        chunks: List[Chunk] = []
        chunk_start_idx = 0
        current_length = len(sentences[0])
        current_sentence_count = 1

        running_centroid: Optional[List[float]] = None
        centroid_count = 0
        if embeddings and self.use_centroid:
            running_centroid, centroid_count = self._build_running_centroid(
                embeddings,
                0,
                0,
            )

        for i in range(1, len(sentences)):
            sentence_len = len(sentences[i])
            would_be_length = current_length + 1 + sentence_len
            split_for_size = would_be_length > self.max_chunk_size
            split_for_span = (
                self.max_sentences_per_chunk is not None
                and (current_sentence_count + 1) > self.max_sentences_per_chunk
            )

            similarity: Optional[float] = None
            if embeddings and len(embeddings) > i:
                if self.use_centroid:
                    if running_centroid and len(running_centroid) == len(embeddings[i]):
                        similarity = self._cosine_similarity(running_centroid, embeddings[i])
                    else:
                        similarity = None
                else:
                    similarity = self._cosine_similarity(embeddings[i - 1], embeddings[i])

            should_split, reason = self._should_split(
                current_chunk_len=current_length,
                similarity=similarity,
                split_for_size=split_for_size,
                split_for_span=split_for_span,
            )

            if self.debug:
                logger.debug(
                    "semantic_chunk step=%s sim=%s split=%s current_len=%s would_len=%s sentence_count=%s",
                    i,
                    None if similarity is None else round(similarity, 4),
                    reason,
                    current_length,
                    would_be_length,
                    current_sentence_count,
                )

            if should_split:
                end_idx = i - 1
                chunk_text = self._chunk_text(sentences, chunk_start_idx, end_idx)
                chunks.append(
                    Chunk(
                        id=uuid.uuid4(),
                        text=chunk_text,
                        metadata=metadata.copy(),
                        start_char=spans[chunk_start_idx][0],
                        end_char=spans[end_idx][1],
                    )
                )

                new_start = max(0, i - self.overlap_sentences)
                chunk_start_idx = new_start
                current_length = self._chunk_char_length(sentences, chunk_start_idx, i)

                current_sentence_count = i - chunk_start_idx + 1
                if embeddings and self.use_centroid:
                    running_centroid, centroid_count = self._build_running_centroid(
                        embeddings,
                        chunk_start_idx,
                        i,
                    )
            else:
                current_length = would_be_length
                current_sentence_count += 1
                if embeddings and self.use_centroid:
                    if running_centroid is None or centroid_count <= 0:
                        running_centroid, centroid_count = self._build_running_centroid(
                            embeddings,
                            chunk_start_idx,
                            i,
                        )
                    else:
                        updated = self._update_centroid(
                            running_centroid,
                            centroid_count,
                            embeddings[i],
                        )
                        if updated:
                            running_centroid = updated
                            centroid_count += 1
                        else:
                            running_centroid = None
                            centroid_count = 0

        final_text = self._chunk_text(sentences, chunk_start_idx, len(sentences) - 1)
        chunks.append(
            Chunk(
                id=uuid.uuid4(),
                text=final_text,
                metadata=metadata.copy(),
                start_char=spans[chunk_start_idx][0],
                end_char=spans[len(sentences) - 1][1],
            )
        )

        return chunks

    def get_config(self) -> Dict[str, Any]:
        """Return the chunker's current configuration.

        Returns:
            A dict containing strategy name and semantic controls.
        """
        return {
            "strategy": "semantic",
            "max_chunk_size": self.max_chunk_size,
            "similarity_threshold": self.similarity_threshold,
            "min_chunk_size": self.min_chunk_size,
            "use_centroid": self.use_centroid,
            "overlap_sentences": self.overlap_sentences,
            "hard_split_threshold": self.hard_split_threshold,
            "max_sentences_per_chunk": self.max_sentences_per_chunk,
            "smoothing_margin": self.smoothing_margin,
            "require_embedder": self.require_embedder,
            "debug": self.debug,
            "embedder_model": self.embedder.model_name if self.embedder else None,
        }
