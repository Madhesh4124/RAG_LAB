import json
import os
from pathlib import Path
import re
from functools import lru_cache
from typing import Literal
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path, override=True)


_INTENT = Literal["global", "local"]


def _get_classifier_client():
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        try:
            from app.services.llm.groq_client import GroqClient
            eval_model = os.getenv("EVALUATION_LLM_MODEL", "openai/gpt-oss-120b")
            client = GroqClient(
                model=eval_model,
                temperature=0.0,
                system_prompt=(
                    "You classify user queries for RAG routing. "
                    "Return ONLY strict JSON with the schema: "
                    '{"intent":"global|local","confidence":0.0-1.0}. '
                    "Use global for whole-document overview/summary intent. "
                    "Use local for specific section/page/fact/detail lookup."
                ),
            )
            if getattr(client, "llm", None):
                return client
        except Exception:
            pass

    # Fallback to NVIDIA NIM
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_api_key:
        try:
            from app.services.llm.nvidia_client import NvidiaClient
            client = NvidiaClient(
                model="nvidia/nemotron-3.5-lightning-30b-a3b",
                temperature=0.0,
                system_prompt=(
                    "You classify user queries for RAG routing. "
                    "Return ONLY strict JSON with the schema: "
                    '{"intent":"global|local","confidence":0.0-1.0}. '
                    "Use global for whole-document overview/summary intent. "
                    "Use local for specific section/page/fact/detail lookup."
                ),
            )
            if getattr(client, "llm", None):
                return client
        except Exception:
            pass

    return None


def _parse_intent(payload: str) -> _INTENT | None:
    text = (payload or "").strip()
    if not text:
        return None

    # Try direct JSON parse first.
    try:
        obj = json.loads(text)
        intent = str(obj.get("intent", "")).strip().lower()
        if intent in ("global", "local"):
            return intent  # type: ignore[return-value]
    except Exception:
        pass

    # Then try extracting an embedded JSON object.
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            intent = str(obj.get("intent", "")).strip().lower()
            if intent in ("global", "local"):
                return intent  # type: ignore[return-value]
        except Exception:
            pass

    lowered = text.lower()
    if '"intent":"global"' in lowered or "intent: global" in lowered:
        return "global"
    if '"intent":"local"' in lowered or "intent: local" in lowered:
        return "local"
    return None


def _fallback_intent(query: str) -> _INTENT:
    # Lightweight lexical fallback if classifier LLM is unavailable.
    q = query.lower()
    global_markers = (
        "summary",
        "summarize",
        "overview",
        "main idea",
        "key points",
        "document about",
        "being trained",
        "trained for",
        "purpose of",
        "objective of",
        "goal of",
    )
    local_markers = ("section", "chapter", "page", "phase", "detail", "explain", "specific")

    if any(marker in q for marker in local_markers):
        return "local"
    if any(marker in q for marker in global_markers):
        return "global"
    return "local"


@lru_cache(maxsize=512)
def _classify_query_cached(normalized_query: str) -> _INTENT:
    client = _get_classifier_client()
    if not client:
        return _fallback_intent(normalized_query)

    prompt = (
        "Classify the following user query for RAG routing. "
        "Return only strict JSON with intent and confidence.\n\n"
        f"Query: {normalized_query}"
    )
    try:
        raw = client.generate(prompt, chunks=[])
        parsed = _parse_intent(raw)
        if parsed:
            return parsed
    except Exception:
        pass

    return _fallback_intent(normalized_query)


def classify_query(query: str) -> _INTENT:
    q = (query or "").strip()
    if not q:
        return "local"

    lowered = q.lower()
    if (
        "being trained" in lowered
        or "trained for" in lowered
        or "trained to do" in lowered
        or ("for what" in lowered and "model" in lowered and "trained" in lowered)
    ):
        return "global"

    return _classify_query_cached(q)
