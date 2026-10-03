"""NVIDIA NIM LLM Client using LangChain's ChatNVIDIA."""

import asyncio
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from app.services.chunking.base import Chunk

env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path, override=True)
logger = logging.getLogger(__name__)


def _build_context(chunks: List[Chunk], max_chunks: int = 8, max_chars: int = 12000) -> str:
    """Compact retrieved context to reduce token count and generation latency."""
    parts: List[str] = []
    total = 0
    for idx, chunk in enumerate(chunks[:max_chunks], start=1):
        metadata = getattr(chunk, "metadata", {}) or {}
        text = (metadata.get("window_text") or getattr(chunk, "text", "") or "").strip()
        if text.startswith("image://") or metadata.get("modality") == "image":
            page = metadata.get("page", "unknown")
            img_name = metadata.get("image_name", "Figure")
            text = f"[Image/Diagram: {img_name} found on Page {page}]"
        elif len(text) > 2000:
            text = text[:2000] + "..."
        segment = f"[Chunk {idx}]\n{text}"
        if total + len(segment) > max_chars:
            break
        parts.append(segment)
        total += len(segment)
    return "\n\n---\n\n".join(parts)


def _content_to_text(content: Any) -> str:
    """Normalize provider content payloads to plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (int, float, bool)):
        return str(content)
    if isinstance(content, dict):
        for key in ("text", "output_text", "content", "parts", "message"):
            value = content.get(key)
            if value is not None:
                extracted = _content_to_text(value)
                if extracted:
                    return extracted
        return ""
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            extracted = _content_to_text(item)
            if extracted:
                parts.append(extracted)
        return "".join(parts)
    return str(content)


class NvidiaClient:
    """NVIDIA NIM LLM Client using LangChain's ChatNVIDIA."""

    DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.2,
        top_p: float = 0.95,
        max_tokens: int = 4096,
        reasoning_budget: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ):
        self.provider = "nvidia"
        if not model or "gemini" in model.lower() or "gemma" in model.lower() or not model.startswith("nvidia/"):
            self.model_name = os.getenv("NVIDIA_LLM_MODEL", self.DEFAULT_MODEL)
        else:
            self.model_name = model
        self.temperature = float(temperature)
        self.top_p = float(top_p)
        self.max_tokens = int(max_tokens)
        
        # Use fast reasoning budget (default 1024) to avoid 4+ minute latency
        env_budget = os.getenv("NVIDIA_REASONING_BUDGET", "1024")
        self.reasoning_budget = int(reasoning_budget) if reasoning_budget is not None else int(env_budget)
        enable_thinking_env = os.getenv("NVIDIA_ENABLE_THINKING", "false").lower() in ("true", "1", "yes")

        self.system_prompt = system_prompt or (
            "You are an expert research assistant. Answer the user's question based on the provided document context below. "
            "Be concise but complete. If the question asks about the title, author, or heading of the document, look for it near the top chunks. "
            "If the answer is genuinely not available in the context, say so clearly. "
            "Do not fabricate facts."
        )

        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            logger.warning("NVIDIA_API_KEY is not set. NVIDIA NIM features will be unavailable.")
            self.llm = None
        else:
            try:
                from langchain_nvidia_ai_endpoints import ChatNVIDIA

                model_kwargs = {}
                if enable_thinking_env:
                    model_kwargs["reasoning_budget"] = self.reasoning_budget
                    model_kwargs["chat_template_kwargs"] = {"enable_thinking": True}

                self.llm = ChatNVIDIA(
                    model=self.model_name,
                    api_key=api_key,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    max_tokens=self.max_tokens,
                    model_kwargs=model_kwargs if model_kwargs else None,
                )
                logger.info(
                    "Initialized ChatNVIDIA client model=%s temperature=%s",
                    self.model_name,
                    self.temperature,
                )
            except Exception as exc:
                logger.warning("Failed to initialize ChatNVIDIA (%s)", exc)
                self.llm = None

    def _build_prompt(self, query: str, chunks: List[Chunk], memory: Any = None) -> List[Dict[str, str]]:
        context = _build_context(chunks)
        history_text = ""
        if memory is not None and hasattr(memory, "get_context"):
            history_text = str(memory.get_context() or "").strip()
            if history_text:
                history_text = f"\n\nConversation History:\n{history_text}"

        system_content = f"{self.system_prompt}\n\nDocument Context:\n{context}{history_text}"
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query},
        ]

    def generate(self, query: str, chunks: List[Chunk]) -> str:
        """Generate response synchronously."""
        if not self.llm:
            raise RuntimeError("NvidiaClient LLM is not initialized (missing NVIDIA_API_KEY).")

        messages = self._build_prompt(query, chunks)
        response = self.llm.invoke(messages)
        text = _content_to_text(getattr(response, "content", "")).strip()
        return text or "I could not generate a grounded answer from the provided context."

    async def generate_async(self, query: str, chunks: List[Chunk], memory: Any = None) -> str:
        """Generate response asynchronously."""
        if not self.llm:
            raise RuntimeError("NvidiaClient LLM is not initialized (missing NVIDIA_API_KEY).")

        messages = self._build_prompt(query, chunks, memory=memory)
        if hasattr(self.llm, "ainvoke"):
            response = await asyncio.wait_for(self.llm.ainvoke(messages), timeout=30.0)
        else:
            response = await asyncio.wait_for(
                asyncio.to_thread(self.llm.invoke, messages), timeout=30.0
            )
        text = _content_to_text(getattr(response, "content", "")).strip()
        return text or "I could not generate a grounded answer from the provided context."

    def generate_stream(self, query: str, chunks: List[Chunk]):
        """Stream response synchronously."""
        if not self.llm:
            return

        messages = self._build_prompt(query, chunks)
        reasoning_buffer = []
        emitted_content = False

        for chunk in self.llm.stream(messages):
            # Check for thinking/reasoning in additional_kwargs
            if getattr(chunk, "additional_kwargs", None) and "reasoning_content" in chunk.additional_kwargs:
                reasoning_text = str(chunk.additional_kwargs.get("reasoning_content") or "")
                if reasoning_text:
                    reasoning_buffer.append(reasoning_text)

            content_text = _content_to_text(getattr(chunk, "content", ""))
            if content_text:
                emitted_content = True
                yield content_text

        # If model only generated reasoning without content, fallback to emitting reasoning
        if not emitted_content and reasoning_buffer:
            yield "".join(reasoning_buffer)

    async def generate_stream_async(self, query: str, chunks: List[Chunk], memory: Any = None):
        """Stream response asynchronously."""
        if not self.llm:
            return

        messages = self._build_prompt(query, chunks, memory=memory)
        reasoning_buffer = []
        emitted_content = False

        if hasattr(self.llm, "astream"):
            async for chunk in self.llm.astream(messages):
                if getattr(chunk, "additional_kwargs", None) and "reasoning_content" in chunk.additional_kwargs:
                    reasoning_text = str(chunk.additional_kwargs.get("reasoning_content") or "")
                    if reasoning_text:
                        reasoning_buffer.append(reasoning_text)

                content_text = _content_to_text(getattr(chunk, "content", ""))
                if content_text:
                    emitted_content = True
                    yield content_text
        else:
            def _sync_stream():
                return list(self.llm.stream(messages))

            chunks_list = await asyncio.to_thread(_sync_stream)
            for chunk in chunks_list:
                if getattr(chunk, "additional_kwargs", None) and "reasoning_content" in chunk.additional_kwargs:
                    reasoning_text = str(chunk.additional_kwargs.get("reasoning_content") or "")
                    if reasoning_text:
                        reasoning_buffer.append(reasoning_text)

                content_text = _content_to_text(getattr(chunk, "content", ""))
                if content_text:
                    emitted_content = True
                    yield content_text

        if not emitted_content and reasoning_buffer:
            yield "".join(reasoning_buffer)

    def generate_with_memory(self, query: str, chunks: List[Chunk], memory: Any) -> str:
        """Generate response based on query, context chunks, and conversation history."""
        return self.generate_async_sync_wrapper(query, chunks, memory=memory)

    def generate_async_sync_wrapper(self, query: str, chunks: List[Chunk], memory: Any = None) -> str:
        messages = self._build_prompt(query, chunks, memory=memory)
        response = self.llm.invoke(messages)
        text = _content_to_text(getattr(response, "content", "")).strip()
        return text or "I could not generate a grounded answer from the provided context."
