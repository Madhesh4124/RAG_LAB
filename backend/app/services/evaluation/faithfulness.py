import re
import json
from typing import List

from app.services.chunking.base import Chunk


class FaithfulnessEvaluator:
    """Evaluates answer faithfulness against retrieved context using LLM-as-judge."""

    def evaluate(self, query: str, answer: str, chunks: List[Chunk], llm_client) -> float:
        if llm_client is None or not hasattr(llm_client, "llm") or llm_client.llm is None:
            raise ValueError("LLM client is not available for faithfulness evaluation.")

        chunks_text = "\n\n".join(
            [f"[{idx + 1}] {getattr(chunk, 'text', str(chunk))}" for idx, chunk in enumerate(chunks)]
        )

        prompt = (
            f"Question: {query}\n\n"
            f"Given these context chunks:\n{chunks_text}\n\n"
            f"And this answer:\n{answer}\n\n"
            "Rate how faithful the answer is to ONLY the provided context. "
            "Score from 0.0 (answer contains information not in context) to 1.0 "
            "(answer is fully supported by context). Reply with ONLY a decimal number."
        )

        response = llm_client.llm.invoke(prompt)
        content = getattr(response, "content", "")
        score = self._parse_score(str(content))
        return max(0.0, min(1.0, score))

    @staticmethod
    def _parse_score(raw_text: str) -> float:
        text = str(raw_text or "").strip()

        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                for key in ("score", "faithfulness", "rating"):
                    value = payload.get(key)
                    if isinstance(value, (int, float)):
                        return float(value)
            if isinstance(payload, (int, float)):
                return float(payload)
        except json.JSONDecodeError:
            pass

        labeled = re.search(
            r"(?:score|faithfulness|rating)\s*[:=]\s*([-+]?\d*\.?\d+)",
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
            raise ValueError(f"Could not parse faithfulness score from evaluator response: {raw_text}")
        return matches[-1]
