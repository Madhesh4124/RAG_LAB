import re


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
        content = getattr(response, "content", "")
        score = self._parse_score(str(content))
        return max(0.0, min(1.0, score))

    @staticmethod
    def _parse_score(raw_text: str) -> float:
        match = re.search(r"[-+]?\d*\.?\d+", raw_text.strip())
        if not match:
            raise ValueError(f"Could not parse answer relevancy score from evaluator response: {raw_text}")
        return float(match.group(0))
