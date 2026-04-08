import asyncio
import logging
import os
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_summary import DocumentSummary
from app.services.chunking.base import Chunk
from app.services.llm.gemini_client import GeminiClient

_DEFAULT_CHUNK_SUMMARY_PROMPT = "Summarize the following document chunk in 2-3 concise bullet points. Keep only essential facts.\n\n"
_DEFAULT_COMBINE_PROMPT = (
    "Combine the following chunk summaries into one coherent document-level summary. "
    "Include: topic, main ideas, and key takeaways. Keep it concise and factual.\n\n"
)

logger = logging.getLogger(__name__)


class SummaryService:
    """Config-scoped document summary persistence and generation utilities."""

    @staticmethod
    async def get_summary(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        config_id: uuid.UUID,
    ) -> Optional[str]:
        stmt = select(DocumentSummary).where(
            DocumentSummary.user_id == user_id,
            DocumentSummary.document_id == document_id,
            DocumentSummary.config_id == config_id,
        )
        record = (await db.execute(stmt)).scalars().first()
        return record.summary if record else None

    @staticmethod
    async def upsert_summary(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        config_id: uuid.UUID,
        summary: str,
    ) -> DocumentSummary:
        stmt = select(DocumentSummary).where(
            DocumentSummary.user_id == user_id,
            DocumentSummary.document_id == document_id,
            DocumentSummary.config_id == config_id,
        )
        record = (await db.execute(stmt)).scalars().first()
        if record is None:
            record = DocumentSummary(
                user_id=user_id,
                document_id=document_id,
                config_id=config_id,
                summary=summary,
            )
            db.add(record)
        else:
            record.summary = summary
            db.add(record)

        await db.flush()
        return record

    @staticmethod
    async def ensure_precomputed_summary(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        config_id: uuid.UUID,
        chunks: List[Chunk],
        llm_client: Optional[GeminiClient],
    ) -> Optional[str]:
        existing = await SummaryService.get_summary(db, user_id, document_id, config_id)
        if existing:
            return existing

        generated = await SummaryService.generate_doc_summary(chunks, llm_client)
        if not generated:
            return None

        await SummaryService.upsert_summary(
            db=db,
            user_id=user_id,
            document_id=document_id,
            config_id=config_id,
            summary=generated,
        )
        return generated

    @staticmethod
    async def generate_doc_summary(
        chunks: List[Chunk],
        llm_client: Optional[GeminiClient],
    ) -> Optional[str]:
        if not chunks or not llm_client or not getattr(llm_client, "llm", None):
            return None

        # Concatenate chunks up to a large context limit (e.g. ~30k chars/7k tokens)
        # Doing this in a single LLM call is infinitely faster than sequential chunk calls.
        # Keep default context moderate to avoid long first-prepare latency.
        try:
            MAX_COMBINED_CHARS = int(os.getenv("DOC_SUMMARY_MAX_CHARS", "12000"))
        except (ValueError, TypeError):
            MAX_COMBINED_CHARS = 12000
        
        try:
            SEPARATOR = os.getenv("DOC_SUMMARY_CHUNK_SEPARATOR", "\n")
        except Exception:
            SEPARATOR = "\n"
        
        full_text_parts = []
        current_len = 0
        for chunk in chunks:
            text = (chunk.text or "").strip()
            if not text:
                continue
            if current_len + len(text) > MAX_COMBINED_CHARS:
                remaining = MAX_COMBINED_CHARS - current_len
                full_text_parts.append(text[:remaining])
                break
            full_text_parts.append(text)
            current_len += len(text)

        if not full_text_parts:
            return None
            
        combined_text = SEPARATOR.join(full_text_parts)
        prompt = (
            "Please read the following document excerpt and provide a coherent, document-level summary. "
            "Include the main topic, core ideas, and key takeaways. Keep it concise, factual, and strictly based on the text below.\n\n"
            f"{combined_text}"
        )
        return await SummaryService._invoke_llm_text(llm_client, prompt)

    @staticmethod
    async def _invoke_llm_text(llm_client: GeminiClient, prompt: str) -> str:
        try:
            timeout_s = float(os.getenv("DOC_SUMMARY_LLM_TIMEOUT_SECONDS", "45"))
        except (ValueError, TypeError):
            timeout_s = 45.0
            
        try:
            if hasattr(llm_client.llm, "ainvoke"):
                response = await asyncio.wait_for(
                    llm_client.llm.ainvoke(prompt),
                    timeout=timeout_s,
                )
            else:
                response = await asyncio.wait_for(
                    asyncio.to_thread(llm_client.llm.invoke, prompt),
                    timeout=timeout_s,
                )
        except asyncio.TimeoutError:
            logger.info(
                "Summary generation timed out after %.1fs; skipping precompute for now",
                timeout_s,
            )
            return ""
        except Exception as e:
            logger.warning("Summary generation failed due to an API error: %s", e)
            return ""
        content = getattr(response, "content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts).strip()
        return str(content).strip()
