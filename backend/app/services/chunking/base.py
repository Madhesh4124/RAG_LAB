"""
Base classes for document chunking.

Defines the Chunk dataclass and the BaseChunker abstract base class
that all chunking strategies must implement.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Chunk:
    """Represents a single chunk of text extracted from a document.

    Attributes:
        id: Unique identifier for the chunk (auto-generated UUID).
        text: The textual content of the chunk.
        metadata: Arbitrary metadata associated with the chunk
                  (e.g., source document, page number).
        start_char: Starting character index of the chunk in the
                    original text (inclusive).
        end_char: Ending character index of the chunk in the
                  original text (exclusive).
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_char: int = 0
    end_char: int = 0


class BaseChunker(ABC):
    """Abstract base class for all chunking strategies.

    Subclasses must implement `chunk()` to split text into a list of
    `Chunk` objects, and `get_config()` to expose the chunker's
    current configuration.
    """

    @abstractmethod
    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """Split *text* into a list of Chunk objects.

        Args:
            text: The full text to be chunked.
            metadata: A dictionary of metadata to attach to each
                      generated chunk.

        Returns:
            A list of Chunk objects produced from the input text.
        """
        ...

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Return the chunker's current settings as a dictionary.

        Returns:
            A dict describing the chunker's configuration
            (e.g., chunk size, overlap, strategy name).
        """
        ...
