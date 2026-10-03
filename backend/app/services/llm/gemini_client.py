"""Gemini LLM Client."""

import asyncio
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from app.services.chunking.base import Chunk

env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path, override=True)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def _build_llm(model_name: str, temperature: float, api_key: str) -> ChatGoogleGenerativeAI:
    max_output_tokens = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "4096"))
    if model_name in ("gemma-4-27b-it", "gemma-4-31b-it", "gemma-4-31b", "gemma-31b", "gemma", "gemini-2.5", "gemma-4-26b-a4b-it"):
        actual_model = "gemini-2.5-flash"
    else:
        actual_model = model_name or "gemini-2.5-flash"
    return ChatGoogleGenerativeAI(
        model=actual_model,
        temperature=temperature,
        google_api_key=api_key,
        max_output_tokens=max_output_tokens,
        max_retries=1,
    )


def _build_context(chunks: List[Chunk], max_chunks: int = 8, max_chars: int = 12000) -> str:
    """Compact retrieved context to reduce token count and generation latency."""
    parts: List[str] = []
    total = 0
    for idx, chunk in enumerate(chunks[:max_chunks], start=1):
        metadata = getattr(chunk, "metadata", {}) or {}
        text = (metadata.get("window_text") or chunk.text or "").strip()
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

def _default_llm_model() -> str:
    return os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash")


class GeminiClient:
    """Gemini Client using LangChain's ChatGoogleGenerativeAI."""

    def __init__(self, model: str = None, temperature: float = 0.2, system_prompt: str = None):
        self.provider = "google"
        self.model_name = model or _default_llm_model()
        self.temperature = temperature
        self.system_prompt = system_prompt or (
            "You are an expert research assistant. Answer the user's question based on the provided document context below. "
            "Be concise but complete. If the question asks about the title, author, or heading of the document, look for it near the top chunks. "
            "If the answer is genuinely not available in the context, say so clearly. "
            "Do not fabricate facts."
        )
        
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning(
                "Neither GEMINI_API_KEY nor GOOGLE_API_KEY is set. "
                "Gemini features will be unavailable; will attempt fallback."
            )
            self.llm = None
        else:
            logger.info(
                "Initializing Gemini LLM client model=%s temperature=%s api_key_present=%s key_prefix=%s",
                self.model_name,
                self.temperature,
                bool(api_key),
                api_key[:12] if api_key else "None",
            )
            try:
                self.llm = _build_llm(self.model_name, float(self.temperature), api_key)
            except Exception as e:
                logger.warning("Failed to initialize ChatGoogleGenerativeAI: %s", e)
                self.llm = None

    @property
    def nvidia_fallback(self):
        """Lazy-loaded NvidiaClient (nvidia/nemotron-3.5-lightning-30b-a3b) as 2nd option."""
        if not hasattr(self, "_nvidia_fallback_instance"):
            try:
                from app.services.llm.nvidia_client import NvidiaClient
                nvidia_key = os.getenv("NVIDIA_API_KEY")
                if nvidia_key:
                    self._nvidia_fallback_instance = NvidiaClient(
                        model=os.getenv("NVIDIA_LLM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b"),
                        temperature=float(self.temperature),
                        system_prompt=self.system_prompt,
                    )
                else:
                    self._nvidia_fallback_instance = None
            except Exception as e:
                logger.warning("Could not instantiate NvidiaClient fallback: %s", e)
                self._nvidia_fallback_instance = None
        return self._nvidia_fallback_instance

    @property
    def groq_fallback(self):
        """Lazy-loaded GroqClient fallback as 3rd option."""
        if not hasattr(self, "_groq_fallback_instance"):
            try:
                from app.services.llm.groq_client import GroqClient
                groq_key = os.getenv("GROQ_API_KEY")
                if groq_key:
                    fallback_model = os.getenv("EVALUATION_LLM_MODEL", "openai/gpt-oss-120b")
                    if "gemini" in fallback_model.lower() or "gemma" in fallback_model.lower():
                        fallback_model = "openai/gpt-oss-120b"
                    self._groq_fallback_instance = GroqClient(
                        model=fallback_model,
                        temperature=float(self.temperature),
                        system_prompt=self.system_prompt,
                    )
                else:
                    self._groq_fallback_instance = None
            except Exception as e:
                logger.warning("Could not instantiate GroqClient fallback: %s", e)
                self._groq_fallback_instance = None
        return self._groq_fallback_instance

    @property
    def fallback_client(self):
        """First available fallback client (prefers NVIDIA NIM, then Groq)."""
        return self.nvidia_fallback or self.groq_fallback

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
        prompt = self._build_prompt(query, chunks)
        if self.llm:
            try:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.llm.invoke, prompt)
                    response = future.result(timeout=4.0)
                text = _content_to_text(getattr(response, "content", "")).strip()
                if text:
                    return text
            except Exception as exc:
                logger.warning("Gemini generation failed or timed out (%s); attempting NVIDIA NIM fallback", exc)

        # 2nd option: NVIDIA NIM
        if self.nvidia_fallback:
            try:
                return self.nvidia_fallback.generate(query, chunks)
            except Exception as nv_exc:
                logger.warning("NVIDIA NIM fallback generation failed (%s); attempting Groq fallback", nv_exc)

        # 3rd option: Groq
        if self.groq_fallback:
            try:
                return self.groq_fallback.generate(query, chunks)
            except Exception as fallback_exc:
                logger.error("Groq fallback generation failed: %s", fallback_exc)

        if not self.llm and not self.nvidia_fallback and not self.groq_fallback:
            raise RuntimeError(
                "LLM client not initialized. Neither Gemini, NVIDIA, nor Groq API keys are available."
            )
        return "I could not generate a grounded answer from the provided context."

    async def generate_async(self, query: str, chunks: List[Chunk], memory: Any = None) -> str:
        """Async generation using LangChain's async model interface when available."""
        prompt = self._build_prompt(query, chunks, memory=memory)
        if self.llm:
            try:
                if hasattr(self.llm, "ainvoke"):
                    response = await asyncio.wait_for(self.llm.ainvoke(prompt), timeout=4.0)
                else:
                    response = await asyncio.wait_for(asyncio.to_thread(self.llm.invoke, prompt), timeout=4.0)
                text = _content_to_text(getattr(response, "content", "")).strip()
                if text:
                    return text
            except Exception as exc:
                logger.warning("Gemini async generation failed or timed out (%s); attempting NVIDIA NIM fallback", exc)

        # 2nd option: NVIDIA NIM
        if self.nvidia_fallback:
            try:
                return await self.nvidia_fallback.generate_async(query, chunks, memory=memory)
            except Exception as nv_exc:
                logger.warning("NVIDIA NIM async generation failed (%s); attempting Groq fallback", nv_exc)

        # 3rd option: Groq
        if self.groq_fallback:
            try:
                return await self.groq_fallback.generate_async(query, chunks, memory=memory)
            except Exception as fallback_exc:
                logger.error("Groq fallback async generation failed: %s", fallback_exc)

        if not self.llm and not self.nvidia_fallback and not self.groq_fallback:
            raise RuntimeError(
                "LLM client not initialized. Neither Gemini, NVIDIA, nor Groq API keys are available."
            )
        return "I could not generate a grounded answer from the provided context."

    def generate_stream(self, query: str, chunks: List[Chunk]):
        """Stream response based on query and context chunks."""
        prompt = self._build_prompt(query, chunks)
        emitted = False
        if self.llm:
            try:
                for chunk in self.llm.stream(prompt):
                    text = _content_to_text(getattr(chunk, "content", ""))
                    if text:
                        emitted = True
                        yield text
                if emitted:
                    return
            except Exception as exc:
                logger.warning("Gemini stream failed (%s); attempting NVIDIA NIM fallback", exc)

        # 2nd option: NVIDIA NIM
        if self.nvidia_fallback:
            try:
                for chunk in self.nvidia_fallback.generate_stream(query, chunks):
                    emitted = True
                    yield chunk
                if emitted:
                    return
            except Exception as nv_exc:
                logger.warning("NVIDIA NIM stream failed (%s); attempting Groq fallback", nv_exc)

        # 3rd option: Groq
        if self.groq_fallback:
            try:
                for chunk in self.groq_fallback.generate_stream(query, chunks):
                    emitted = True
                    yield chunk
                if emitted:
                    return
            except Exception as fallback_exc:
                logger.error("Groq fallback stream failed: %s", fallback_exc)

        if not emitted:
            yield "I could not generate a grounded answer from the provided context."

    async def generate_stream_async(self, query: str, chunks: List[Chunk], memory: Any = None):
        """Async stream response based on query and context chunks."""
        prompt = self._build_prompt(query, chunks, memory=memory)
        emitted = False
        if self.llm:
            try:
                if hasattr(self.llm, "astream"):
                    first_token = True
                    stream_iter = self.llm.astream(prompt)
                    while True:
                        try:
                            # Allow up to 25s for TTFT under network jitter/high demand; 10s for subsequent tokens
                            token_timeout = 25.0 if first_token else 10.0
                            chunk = await asyncio.wait_for(stream_iter.__anext__(), timeout=token_timeout)
                            first_token = False
                        except StopAsyncIteration:
                            break
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
                if emitted:
                    return
            except Exception as exc:
                logger.warning("Gemini async stream failed or timed out (%s); attempting NVIDIA NIM fallback", exc)

        # 2nd option: NVIDIA NIM
        if self.nvidia_fallback:
            try:
                async for chunk in self.nvidia_fallback.generate_stream_async(query, chunks, memory=memory):
                    emitted = True
                    yield chunk
                if emitted:
                    return
            except Exception as nv_exc:
                logger.warning("NVIDIA NIM async stream failed (%s); attempting Groq fallback", nv_exc)

        # 3rd option: Groq
        if self.groq_fallback:
            try:
                async for chunk in self.groq_fallback.generate_stream_async(query, chunks, memory=memory):
                    emitted = True
                    yield chunk
                if emitted:
                    return
            except Exception as fallback_exc:
                logger.error("Groq fallback async stream failed: %s", fallback_exc)

        if not emitted:
            yield "I could not generate a grounded answer from the provided context."

    def generate_with_memory(self, query: str, chunks: List[Chunk], memory: Any) -> str:
        """Generate response based on query, context chunks, and conversation history."""
        prompt = self._build_memory_prompt(query, chunks, memory)
        if self.llm:
            try:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.llm.invoke, prompt)
                    response = future.result(timeout=4.0)
                text = _content_to_text(getattr(response, "content", "")).strip()
                if text:
                    return text
            except Exception as exc:
                logger.warning("Gemini memory generation failed (%s); attempting NVIDIA NIM fallback", exc)

        if self.nvidia_fallback:
            try:
                return self.nvidia_fallback.generate_with_memory(query, chunks, memory)
            except Exception as nv_exc:
                logger.warning("NVIDIA NIM memory generation failed (%s); attempting Groq fallback", nv_exc)

        if self.groq_fallback:
            try:
                return self.groq_fallback.generate_with_memory(query, chunks, memory)
            except Exception as fallback_exc:
                logger.error("Groq memory generation fallback failed: %s", fallback_exc)

        return "I could not generate a grounded answer from the provided context."

    def generate_stream_with_memory(self, query: str, chunks: List[Chunk], memory: Any):
        """Stream response based on query, memory and context."""
        prompt = self._build_memory_prompt(query, chunks, memory)
        emitted = False
        if self.llm:
            try:
                for chunk in self.llm.stream(prompt):
                    text = _content_to_text(getattr(chunk, "content", ""))
                    if text:
                        emitted = True
                        yield text
                if emitted:
                    return
            except Exception as exc:
                logger.warning("Gemini generate_stream_with_memory failed (%s); attempting NVIDIA NIM fallback", exc)

        # 2nd option: NVIDIA NIM
        if self.nvidia_fallback:
            try:
                for chunk in self.nvidia_fallback.generate_stream(query, chunks):
                    emitted = True
                    yield chunk
                if emitted:
                    return
            except Exception as nv_exc:
                logger.warning("NVIDIA NIM stream with memory failed (%s); attempting Groq fallback", nv_exc)

        # 3rd option: Groq
        if self.groq_fallback:
            try:
                for chunk in self.groq_fallback.generate_stream_with_memory(query, chunks, memory):
                    emitted = True
                    yield chunk
                if emitted:
                    return
            except Exception as fallback_exc:
                logger.error("Groq fallback generate_stream_with_memory failed: %s", fallback_exc)

        if not emitted:
            yield "I could not generate a grounded answer from the provided context."

    def _build_memory_prompt(self, query: str, chunks: List[Chunk], memory: Any) -> str:
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

    async def ainvoke_prompt(self, prompt: str, timeout: float = 45.0) -> str:
        """Execute a prompt directly with 3-tier fallback: Gemini -> NVIDIA -> Groq."""
        # 1st option: Gemini
        if self.llm:
            try:
                if hasattr(self.llm, "ainvoke"):
                    response = await asyncio.wait_for(self.llm.ainvoke(prompt), timeout=timeout)
                else:
                    response = await asyncio.wait_for(asyncio.to_thread(self.llm.invoke, prompt), timeout=timeout)
                text = _content_to_text(getattr(response, "content", "")).strip()
                if text:
                    return text
            except Exception as exc:
                logger.warning("Gemini ainvoke_prompt failed (%s); attempting NVIDIA NIM fallback", exc)

        # 2nd option: NVIDIA NIM
        if self.nvidia_fallback and self.nvidia_fallback.llm:
            try:
                if hasattr(self.nvidia_fallback.llm, "ainvoke"):
                    response = await asyncio.wait_for(self.nvidia_fallback.llm.ainvoke(prompt), timeout=timeout)
                else:
                    response = await asyncio.wait_for(asyncio.to_thread(self.nvidia_fallback.llm.invoke, prompt), timeout=timeout)
                text = _content_to_text(getattr(response, "content", "")).strip()
                if text:
                    return text
            except Exception as nv_exc:
                logger.warning("NVIDIA NIM ainvoke_prompt failed (%s); attempting Groq fallback", nv_exc)

        # 3rd option: Groq
        if self.groq_fallback and self.groq_fallback.llm:
            try:
                if hasattr(self.groq_fallback.llm, "ainvoke"):
                    response = await asyncio.wait_for(self.groq_fallback.llm.ainvoke(prompt), timeout=timeout)
                else:
                    response = await asyncio.wait_for(asyncio.to_thread(self.groq_fallback.llm.invoke, prompt), timeout=timeout)
                text = _content_to_text(getattr(response, "content", "")).strip()
                if text:
                    return text
            except Exception as fallback_exc:
                logger.error("Groq ainvoke_prompt fallback failed: %s", fallback_exc)

        return ""

    def invoke_prompt(self, prompt: str, timeout: float = 45.0) -> str:
        """Synchronous prompt execution with 3-tier fallback: Gemini -> NVIDIA -> Groq."""
        # 1st option: Gemini
        if self.llm:
            try:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.llm.invoke, prompt)
                    response = future.result(timeout=timeout)
                text = _content_to_text(getattr(response, "content", "")).strip()
                if text:
                    return text
            except Exception as exc:
                logger.warning("Gemini invoke_prompt failed (%s); attempting NVIDIA NIM fallback", exc)

        # 2nd option: NVIDIA NIM
        if self.nvidia_fallback and self.nvidia_fallback.llm:
            try:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.nvidia_fallback.llm.invoke, prompt)
                    response = future.result(timeout=timeout)
                text = _content_to_text(getattr(response, "content", "")).strip()
                if text:
                    return text
            except Exception as nv_exc:
                logger.warning("NVIDIA NIM invoke_prompt failed (%s); attempting Groq fallback", nv_exc)

        # 3rd option: Groq
        if self.groq_fallback and self.groq_fallback.llm:
            try:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.groq_fallback.llm.invoke, prompt)
                    response = future.result(timeout=timeout)
                text = _content_to_text(getattr(response, "content", "")).strip()
                if text:
                    return text
            except Exception as fallback_exc:
                logger.error("Groq invoke_prompt fallback failed: %s", fallback_exc)

        return ""

    def get_config(self) -> Dict[str, Any]:
        """Return the client configuration."""
        return {
            "provider": self.provider,
            "model": self.model_name,
            "temperature": self.temperature,
        }
