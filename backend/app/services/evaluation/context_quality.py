import json
import re
from typing import Dict, List

from app.services.chunking.base import Chunk


class ContextQualityEvaluator:
    """Evaluates context precision and recall using LLM-as-judge."""

    def evaluate(self, query: str, answer: str, chunks: List[Chunk], llm_client) -> Dict[str, float]:
        if llm_client is None or not hasattr(llm_client, "llm") or llm_client.llm is None:
            raise ValueError("LLM client is not available for context quality evaluation.")

        if not chunks:
            return {"context_precision": 0.0, "context_recall": 0.0}

        chunks_text = "\n\n".join(
            [f"[{idx + 1}] {getattr(chunk, 'text', str(chunk))}" for idx, chunk in enumerate(chunks)]
        )

        precision_prompt = (
            f"For each chunk below, is it relevant to answering '{query}'? "
            "Reply with a JSON list of true/false for each chunk.\n\n"
            f"Chunks:\n{chunks_text}"
        )
        precision_response = llm_client.llm.invoke(precision_prompt)
        precision_flags = self._parse_bool_list(getattr(precision_response, "content", ""), expected_len=len(chunks))
        relevant_count = sum(1 for flag in precision_flags if flag)
        context_precision = relevant_count / len(chunks)

        recall_prompt = (
            f"Does the answer '{answer}' miss any important information that would require "
            "additional context beyond what's in these chunks? "
            "Score 0.0-1.0 where 1.0 means the chunks fully cover what's needed."
        )
        recall_response = llm_client.llm.invoke(recall_prompt)
        context_recall = self._parse_score(getattr(recall_response, "content", ""))

        return {
            "context_precision": max(0.0, min(1.0, context_precision)),
            "context_recall": max(0.0, min(1.0, context_recall)),
        }

    @staticmethod
    def _parse_bool_list(raw_text: str, expected_len: int) -> List[bool]:
        text = raw_text.strip()
        match = re.search(r"\[[\s\S]*\]", text)
        candidate = match.group(0) if match else text

        normalized = candidate.replace("True", "true").replace("False", "false")
        data = json.loads(normalized)

        if not isinstance(data, list):
            raise ValueError(f"Could not parse boolean list from evaluator response: {raw_text}")

        bools = [bool(item) for item in data][:expected_len]
        if len(bools) < expected_len:
            bools.extend([False] * (expected_len - len(bools)))
        return bools

    @staticmethod
    def _parse_score(raw_text: str) -> float:
        match = re.search(r"[-+]?\d*\.?\d+", str(raw_text).strip())
        if not match:
            raise ValueError(f"Could not parse context recall score from evaluator response: {raw_text}")
        return float(match.group(0))
