"""Gemini LLM Client."""

import asyncio
import os
from functools import lru_cache
from typing import Any, Dict, List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from app.services.chunking.base import Chunk

load_dotenv(override=True)


@lru_cache(maxsize=8)
def _build_llm(model_name: str, temperature: float, api_key: str) -> ChatGoogleGenerativeAI:
    max_output_tokens = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "1024"))
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=api_key,
        max_output_tokens=max_output_tokens,
    )


def _build_context(chunks: List[Chunk], max_chunks: int = 8, max_chars: int = 12000) -> str:
    """Compact retrieved context to reduce token count and generation latency."""
    parts: List[str] = []
    total = 0
    for idx, chunk in enumerate(chunks[:max_chunks], start=1):
        text = (chunk.text or "").strip()
        if len(text) > 2000:
            text = text[:2000] + "..."
        segment = f"[Chunk {idx}]\n{text}"
        if total + len(segment) > max_chars:
            break
        parts.append(segment)
        total += len(segment)
    return "\n\n---\n\n".join(parts)


def _content_to_text(content: Any) -> str:
    """Normalize provider content payloads (str/list/dict) to plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (int, float, bool)):
        return str(content)
    if isinstance(content, dict):
        # Many providers return rich dict payloads. Prefer text-bearing keys first.
        for key in ("text", "output_text", "content", "parts", "message"):
            value = content.get(key)
            if value is not None:
                extracted = _content_to_text(value)
                if extracted:
                    return extracted

        # If there is no textual content and this block is explicitly reasoning,
        # suppress it from end-user output.
        if content.get("type") in {"thinking", "thought"}:
            return ""
        if "thinking" in content and not any(k in content for k in ("text", "parts", "content", "output_text")):
            return ""

        # Last resort: avoid dumping raw dict repr to users.
        return ""
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            extracted = _content_to_text(item)
            if extracted:
                parts.append(extracted)
        return "".join(parts)
    return str(content)

class GeminiClient:
    """Gemini Client using LangChain's ChatGoogleGenerativeAI."""

    def __init__(self, model: str = "gemma-4-26b-a4b-it", temperature: float = 0.2, system_prompt: str = None):
        self.provider = "google"
        self.model_name = model
        self.temperature = temperature
        self.system_prompt = system_prompt or (
            "You are an expert research assistant. Answer the user's question based on the provided document context below. "
            "Be concise but complete. If the question asks about the title, author, or heading of the document, look for it near the top chunks. "
            "If the answer is genuinely not available in the context, say so clearly. "
            "Do not fabricate facts."
        )
        
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            import logging
            logging.warning(
                "Neither GEMINI_API_KEY nor GOOGLE_API_KEY is set. "
                "LLM features will be unavailable."
            )
            self.llm = None
            return

        self.llm = _build_llm(self.model_name, float(self.temperature), api_key)

    def _format_chunks(self, chunks: List[Chunk]) -> str:
        if not chunks:
            return "No context provided."
        return "\n\n".join([f"[{i+1}] {c.text}" for i, c in enumerate(chunks)])

    def _build_prompt(self, query: str, chunks: List[Chunk], memory: Any = None) -> str:
        context = _build_context(chunks)
        if memory is not None and hasattr(memory, "get") and memory.get():
            return self._build_memory_prompt(query, chunks, memory)
        return f"{self.system_prompt}\n\nDocument Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"

    def generate(self, query: str, chunks: List[Chunk]) -> str:
        """Generate response based on query and context chunks."""
        if not self.llm:
            raise RuntimeError(
                "LLM client not initialized. GEMINI_API_KEY/GOOGLE_API_KEY is missing."
            )
            
        prompt = self._build_prompt(query, chunks)
        
        response = self.llm.invoke(prompt)
        text = _content_to_text(getattr(response, "content", "")).strip()
        if text:
            return text
        return "I could not generate a grounded answer from the provided context."

    async def generate_async(self, query: str, chunks: List[Chunk], memory: Any = None) -> str:
        """Async generation using LangChain's async model interface when available."""
        if not self.llm:
            raise RuntimeError(
                "LLM client not initialized. GEMINI_API_KEY/GOOGLE_API_KEY is missing."
            )

        prompt = self._build_prompt(query, chunks, memory=memory)
        if hasattr(self.llm, "ainvoke"):
            response = await self.llm.ainvoke(prompt)
        else:
            response = await asyncio.to_thread(self.llm.invoke, prompt)

        text = _content_to_text(getattr(response, "content", "")).strip()
        if text:
            return text
        return "I could not generate a grounded answer from the provided context."

    def generate_stream(self, query: str, chunks: List[Chunk]):
        """Stream response based on query and context chunks."""
        if not self.llm:
            raise RuntimeError("LLM client not initialized.")
            
        context = _build_context(chunks)
        prompt = f"{self.system_prompt}\n\nDocument Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        
        emitted = False
        for chunk in self.llm.stream(prompt):
            text = _content_to_text(getattr(chunk, "content", ""))
            if text:
                emitted = True
                yield text
        if not emitted:
            yield "I could not generate a grounded answer from the provided context."

    async def generate_stream_async(self, query: str, chunks: List[Chunk], memory: Any = None):
        """Async stream response based on query and context chunks."""
        if not self.llm:
            raise RuntimeError("LLM client not initialized.")

        prompt = self._build_prompt(query, chunks, memory=memory)
        emitted = False

        if hasattr(self.llm, "astream"):
            async for chunk in self.llm.astream(prompt):
                text = _content_to_text(getattr(chunk, "content", ""))
                if text:
                    emitted = True
                    yield text
        else:
            for piece in self.llm.stream(prompt):
                text = _content_to_text(getattr(piece, "content", ""))
                if text:
                    emitted = True
                    yield text

        if not emitted:
            yield "I could not generate a grounded answer from the provided context."

    def generate_with_memory(self, query: str, chunks: List[Chunk], memory: Any) -> str:
        """Generate response based on query, context chunks, and conversation history."""
        prompt = self._build_memory_prompt(query, chunks, memory)
        response = self.llm.invoke(prompt)
        text = _content_to_text(getattr(response, "content", "")).strip()
        if text:
            return text
        return "I could not generate a grounded answer from the provided context."

    def generate_stream_with_memory(self, query: str, chunks: List[Chunk], memory: Any):
        """Stream response based on query, memory and context."""
        prompt = self._build_memory_prompt(query, chunks, memory)
        emitted = False
        for chunk in self.llm.stream(prompt):
            text = _content_to_text(getattr(chunk, "content", ""))
            if text:
                emitted = True
                yield text
        if not emitted:
            yield "I could not generate a grounded answer from the provided context."

    def _build_memory_prompt(self, query: str, chunks: List[Chunk], memory: Any) -> str:
        if not self.llm:
            raise RuntimeError("LLM client not initialized.")

        context = _build_context(chunks)  # use the capped builder, not _format_chunks

        history_str = ""
        if memory is not None and hasattr(memory, "get"):
            turns = memory.get()
            if turns:
                lines = []
                for turn in turns:
                    role = turn.get("role", "user")
                    content = turn.get("content", "")[:300]  # cap each turn
                    lines.append(f"{role.capitalize()}: {content}")
                history_str = "\n".join(lines)

        if history_str:
            return (
                f"{self.system_prompt}\n\n"
                f"Document Context:\n{context}\n\n"
                f"Conversation so far:\n{history_str}\n\n"
                f"New Question: {query}\n\nAnswer:"
            )

        return f"{self.system_prompt}\n\nDocument Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"

    def get_config(self) -> Dict[str, Any]:
        """Return the client configuration."""
        return {
            "provider": self.provider,
            "model": self.model_name,
            "temperature": self.temperature,
        }
