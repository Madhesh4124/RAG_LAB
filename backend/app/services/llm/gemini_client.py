"""Gemini LLM Client."""

import os
from functools import lru_cache
from typing import Any, Dict, List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from app.services.chunking.base import Chunk

load_dotenv(override=True)


@lru_cache(maxsize=8)
def _build_llm(model_name: str, temperature: float, api_key: str) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=api_key,
        max_output_tokens=512,
    )


def _build_context(chunks: List[Chunk], max_chunks: int = 4, max_chars: int = 6000) -> str:
    """Compact retrieved context to reduce token count and generation latency."""
    parts: List[str] = []
    total = 0
    for idx, chunk in enumerate(chunks[:max_chunks], start=1):
        text = (chunk.text or "").strip()
        if len(text) > 1200:
            text = text[:1200] + "..."
        segment = f"[Chunk {idx}]\n{text}"
        if total + len(segment) > max_chars:
            break
        parts.append(segment)
        total += len(segment)
    return "\n\n---\n\n".join(parts)

class GeminiClient:
    """Gemini Client using LangChain's ChatGoogleGenerativeAI."""

    def __init__(self, model: str = "gemini-2.5-flash", temperature: float = 0.2):
        self.provider = "google"
        self.model_name = model
        self.temperature = temperature
        
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

    def generate(self, query: str, chunks: List[Chunk]) -> str:
        """Generate response based on query and context chunks."""
        if not self.llm:
            raise RuntimeError(
                "LLM client not initialized. GEMINI_API_KEY/GOOGLE_API_KEY is missing."
            )
            
        chunks_text = _build_context(chunks)
        prompt = (
            "Use only the provided context to answer. "
            "If context is insufficient, clearly say so.\n\n"
            f"Context:\n{chunks_text}\n\nQuestion: {query}"
        )
        
        response = self.llm.invoke(prompt)
        # LangChain's AIMessage object has a .content string
        return response.content

    def generate_with_memory(self, query: str, chunks: List[Chunk], context: str) -> str:
        """Generate response based on query, context chunks, and conversation history."""
        if not self.llm:
            raise RuntimeError(
                "LLM client not initialized. GEMINI_API_KEY/GOOGLE_API_KEY is missing."
            )
            
        chunks_text = _build_context(chunks)
        prompt = (
            f"Conversation History:\n{context}\n\n"
            "Use only the provided context to answer. "
            "If context is insufficient, clearly say so.\n\n"
            f"Context:\n{chunks_text}\n\nQuestion: {query}"
        )
        
        response = self.llm.invoke(prompt)
        return response.content

    def get_config(self) -> Dict[str, Any]:
        """Return the client configuration."""
        return {
            "provider": self.provider,
            "model": self.model_name,
            "temperature": self.temperature,
        }
