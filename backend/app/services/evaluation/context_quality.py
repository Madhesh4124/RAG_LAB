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
        raw_prec = getattr(precision_response, "content", "")
        from app.services.evaluation.retrieval_metrics import _extract_text_content
        prec_content = _extract_text_content(raw_prec).strip()
        import logging
        logging.getLogger(__name__).warning("ContextQualityEvaluator precision raw: %r, extracted: %r", raw_prec, prec_content)
        
        precision_flags = self._parse_bool_list(prec_content, expected_len=len(chunks))
        relevant_count = sum(1 for flag in precision_flags if flag)
        context_precision = relevant_count / len(chunks)

        recall_prompt = (
            f"Does the answer '{answer}' miss any important information that would require "
            "additional context beyond what's in these chunks? "
            "Score 0.0-1.0 where 1.0 means the chunks fully cover what's needed."
        )
        recall_response = llm_client.llm.invoke(recall_prompt)
        raw_recall = getattr(recall_response, "content", "")
        recall_content = _extract_text_content(raw_recall).strip()
        logging.getLogger(__name__).warning("ContextQualityEvaluator recall raw: %r, extracted: %r", raw_recall, recall_content)
        
        context_recall = self._parse_score(recall_content)

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

        bools = []
        for item in data[:expected_len]:
            if isinstance(item, bool):
                bools.append(item)
            elif isinstance(item, str):
                bools.append(item.strip().lower() in {"true", "yes", "1"})
            else:
                bools.append(bool(item))
        if len(bools) < expected_len:
            bools.extend([False] * (expected_len - len(bools)))
        return bools

    @staticmethod
    def _parse_score(raw_text: str) -> float:
        text = str(raw_text or "").strip()
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                for key in ("score", "context_recall", "recall", "rating"):
                    value = payload.get(key)
                    if isinstance(value, (int, float)):
                        return float(value)
            if isinstance(payload, (int, float)):
                return float(payload)
        except json.JSONDecodeError:
            pass

        labeled = re.search(
            r"(?:score|context[_\s-]*recall|recall|rating)\s*[:=]\s*([-+]?\d*\.?\d+)",
            text,
            flags=re.IGNORECASE,
        )
        if labeled:
            return float(labeled.group(1))

        first_line = text.splitlines()[0] if text else ""
        first_line_match = re.search(r"^\s*([-+]?\d*\.?\d+)\s*$", first_line)
        if first_line_match:
            return float(first_line_match.group(1))

        matches = [float(item) for item in re.findall(r"[-+]?\d*\.?\d+", text)]
        in_range = [value for value in matches if 0.0 <= value <= 1.0]
        if in_range:
            return in_range[-1]

        if not matches:
            raise ValueError(f"Could not parse context recall score from evaluator response: {raw_text}")
        return matches[-1]
