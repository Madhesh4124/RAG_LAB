import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class MemoryEntry:
    query: str
    response: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class BaseMemory(abc.ABC):
    @abc.abstractmethod
    def add_interaction(self, query: str, response: str) -> None:
        """Stores a new interaction."""
        pass
        
    @abc.abstractmethod
    def get_context(self) -> str:
        """Returns a formatted string of past interactions ready to be injected into an LLM prompt."""
        pass
        
    @abc.abstractmethod
    def clear(self) -> None:
        """Resets all stored memory."""
        pass
        
    @abc.abstractmethod
    def get_summary(self) -> str:
        """Returns a brief string summary of what's been discussed."""
        pass
