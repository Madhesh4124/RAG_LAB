import re
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
        match = re.search(r"[-+]?\d*\.?\d+", raw_text.strip())
        if not match:
            raise ValueError(f"Could not parse faithfulness score from evaluator response: {raw_text}")
        return float(match.group(0))
