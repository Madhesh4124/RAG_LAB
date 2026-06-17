import re
import json


class AnswerRelevancyEvaluator:
    """Evaluates how well an answer addresses the user query using LLM-as-judge."""

    def evaluate(self, query: str, answer: str, llm_client) -> float:
        if llm_client is None or not hasattr(llm_client, "llm") or llm_client.llm is None:
            raise ValueError("LLM client is not available for answer relevancy evaluation.")

        prompt = (
            f"Given the question: '{query}'\n"
            f"And the answer: '{answer}'\n"
            "Rate how well the answer addresses the question from 0.0 (completely irrelevant) "
            "to 1.0 (perfectly answers the question). Reply with ONLY a decimal number."
        )

        response = llm_client.llm.invoke(prompt)
        raw_content = getattr(response, "content", "")
        from app.services.evaluation.retrieval_metrics import _extract_text_content
        content = _extract_text_content(raw_content).strip()
        import logging
        logging.getLogger(__name__).warning("AnswerRelevancyEvaluator raw: %r, extracted: %r", raw_content, content)
        score = self._parse_score(content)
        return max(0.0, min(1.0, score))

    @staticmethod
    def _parse_score(raw_text: str) -> float:
        text = str(raw_text or "").strip()

        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                for key in ("score", "answer_relevancy", "relevancy", "rating"):
                    value = payload.get(key)
                    if isinstance(value, (int, float)):
                        return float(value)
            if isinstance(payload, (int, float)):
                return float(payload)
        except json.JSONDecodeError:
            pass

        labeled = re.search(
            r"(?:score|answer[_\s-]*relevancy|relevancy|rating)\s*[:=]\s*([-+]?\d*\.?\d+)",
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
            raise ValueError(f"Could not parse answer relevancy score from evaluator response: {raw_text}")
        return matches[-1]
