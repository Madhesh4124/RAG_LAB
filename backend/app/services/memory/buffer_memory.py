from collections import deque
from typing import Dict, Any
from app.services.memory.base import BaseMemory, MemoryEntry

class BufferMemory(BaseMemory):
    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self.buffer = deque(maxlen=max_turns)
        
    def add_interaction(self, query: str, response: str) -> None:
        entry = MemoryEntry(query=query, response=response)
        self.buffer.append(entry)
        
    def get_context(self) -> str:
        if not self.buffer:
            return ""
        
        context_parts = []
        for i, entry in enumerate(self.buffer, 1):
            context_parts.append(f"Turn {i}:\nUser: {entry.query}\nAssistant: {entry.response}")
        return "\n\n".join(context_parts)
        
    def clear(self) -> None:
        self.buffer.clear()
        
    def get_summary(self) -> str:
        return f"{len(self.buffer)} turns stored out of {self.max_turns} max."
        
    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "buffer",
            "max_turns": self.max_turns,
            "current_turns": len(self.buffer)
        }
