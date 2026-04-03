from typing import List, Callable, Optional, Dict, Any
from app.services.memory.base import BaseMemory, MemoryEntry

class SummaryMemory(BaseMemory):
    def __init__(self, max_turns_before_summary: int = 5, summarizer_fn: Optional[Callable[[str], str]] = None):
        self.max_turns_before_summary = max_turns_before_summary
        self.summarizer_fn = summarizer_fn
        self.buffer: List[MemoryEntry] = []
        self.summary: str = ""
        
    def add_interaction(self, query: str, response: str) -> None:
        entry = MemoryEntry(query=query, response=response)
        self.buffer.append(entry)
        
        # Check if the buffer surpassed our turn capacity before a mandatory prune/summarization
        if len(self.buffer) > self.max_turns_before_summary:
            if self.summarizer_fn:
                buffer_text = self._format_buffer()
                new_summary_part = self.summarizer_fn(buffer_text)
                
                # Append to persistent summary string
                if self.summary:
                    self.summary += f"\n{new_summary_part}"
                else:
                    self.summary = new_summary_part
                    
                self.buffer.clear()
            else:
                # Fallback: forcefully drop oldest context logic keeping strictly only the last 3 turns
                self.buffer = self.buffer[-3:]
                
    def _format_buffer(self) -> str:
        if not self.buffer:
            return ""
        parts = []
        for entry in self.buffer:
            parts.append(f"User: {entry.query}\nAssistant: {entry.response}")
        return "\n\n".join(parts)
        
    def get_context(self) -> str:
        context_parts = []
        if self.summary:
            context_parts.append(f"Historical Conversation Summary:\n{self.summary}")
            
        buffer_context = self._format_buffer()
        if buffer_context:
            context_parts.append(f"Recent Conversation:\n{buffer_context}")
            
        return "\n\n".join(context_parts)
        
    def get(self) -> list:
        history = []
        if self.summary:
            history.append({"role": "system", "content": f"Historical Conversation Summary:\n{self.summary}"})
        for entry in self.buffer:
            history.append({"role": "user", "content": entry.query})
            history.append({"role": "assistant", "content": entry.response})
        return history
        
    def clear(self) -> None:
        self.buffer.clear()
        self.summary = ""
        
    def get_summary(self) -> str:
        if self.summary:
            return f"Historical Summary: {self.summary}\n(+{len(self.buffer)} recent unsummarized turns)"
        return f"No historical summary logged. {len(self.buffer)} recent sequential turns mapped."
        
    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "summary",
            "max_turns_before_summary": self.max_turns_before_summary,
            "has_summarizer_fn": self.summarizer_fn is not None,
            "current_buffer_size": len(self.buffer)
        }
