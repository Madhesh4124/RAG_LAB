"""
NVIDIA AI Endpoints embedding strategy.

Uses LangChain's NVIDIAEmbeddings to produce vector
embeddings via NVIDIA's text-embedding models.
"""

import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

from app.services.embedding.base import BaseEmbedder

load_dotenv()


class NvidiaEmbedder(BaseEmbedder):
    """Embedder backed by NVIDIA AI Endpoints (via LangChain).

    Supported models include:
      - nvidia/nv-embed-v1
      - nvidia/llama-3.2-nemoretriever-300m-embed-v1

    Args:
        model: The NVIDIA embedding model identifier.
               Defaults to ``"nvidia/nv-embed-v1"``.

    Raises:
        ValueError: If *NVIDIA_API_KEY* is not set in the environment
                    or ``.env`` file.
    """

    def __init__(self, model: str = "nvidia/nv-embed-v1") -> None:
        self.model = model

        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError(
                "NVIDIA_API_KEY is not set. "
                "Please add it to your .env file."
            )

        self._embeddings = NVIDIAEmbeddings(
            model=self.model,
            api_key=api_key,
            truncate="NONE",
        )

    # ── BaseEmbedder interface ──────────────────────────────────────

    @property
    def model_name(self) -> str:
        """The name of the embedding model."""
        return self.model

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string using NVIDIA's embedding model.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return self._embeddings.embed_query(text)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                # Usually 502/429 are thrown as Exception/requests.exceptions.HTTPError
                error_msg = str(e)
                if "502" in error_msg or "429" in error_msg or "Gateway" in error_msg:
                    time.sleep(2 ** attempt)
                    continue
                raise

    def _embed_batch_with_retry(self, texts: List[str]) -> List[List[float]]:
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return self._embeddings.embed_documents(texts)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                error_msg = str(e)
                if "502" in error_msg or "429" in error_msg or "Gateway" in error_msg or "RateLimit" in error_msg:
                    time.sleep(2 ** attempt)
                    continue
                raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings using NVIDIA's embedding model.

        Args:
            texts: A list of texts to embed.

        Returns:
            A list of embedding vectors, one per input text.
        """
        import os
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            worker_limit = int(os.environ.get("MAX_CONCURRENT_EMBEDDING_WORKERS", 5))
        except ValueError:
            worker_limit = 5
            
        try:
            batch_size = int(os.environ.get("NVIDIA_EMBEDDING_BATCH_SIZE", 50))
        except ValueError:
            batch_size = 50

        if len(texts) <= batch_size:
            return self._embed_batch_with_retry(texts)

        batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        max_workers = min(worker_limit, len(batches))
        
        ordered_results = [None] * len(batches)
        
        def process_batch(args):
            idx, batch_texts = args
            return idx, self._embed_batch_with_retry(batch_texts)
            
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for idx, batch_embeddings in executor.map(process_batch, enumerate(batches)):
                ordered_results[idx] = batch_embeddings
                
        results = []
        for batch_embeddings in ordered_results:
            if batch_embeddings:
                results.extend(batch_embeddings)
                
        return results
                
    def get_config(self) -> Dict[str, Any]:
        """Return the embedder's configuration.

        Returns:
            A dict with *strategy*, *model*, and *provider* keys.
        """
        return {
            "strategy": "nvidia_ai_endpoints",
            "model": self.model,
            "provider": "NVIDIA",
        }
