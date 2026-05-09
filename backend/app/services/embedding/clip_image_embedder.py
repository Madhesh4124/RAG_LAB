"""Local CLIP embedder for text-to-image retrieval.

This embedder uses a free Hugging Face model locally. It supports normal text
queries via CLIP text features and image chunks represented as ``image://KEY``
URIs via CLIP image features.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
import threading
from typing import Any, Dict, List

from PIL import Image

from app.services.embedding.base import BaseEmbedder
from app.services.file_storage import get_file_storage

logger = logging.getLogger(__name__)

_MODEL_CACHE: dict[str, tuple[Any, Any, Any]] = {}
_MODEL_CACHE_LOCK = threading.Lock()


class CLIPImageEmbedder(BaseEmbedder):
    """Embed text queries and image chunks in the same CLIP vector space."""

    def __init__(
        self,
        model: str | None = None,
        device: str | None = None,
    ) -> None:
        self._model_name = model or os.getenv(
            "HF_IMAGE_EMBEDDING_MODEL",
            "openai/clip-vit-base-patch32",
        )
        self.device = device or os.getenv("IMAGE_EMBEDDING_DEVICE", "cpu")

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_text(self, text: str) -> List[float]:
        backend, model, processor_or_none, torch_or_none = self._load_model()

        if backend == "qwen3_vl_st":
            vectors = model.encode(
                [{"text": text or ""}],
                normalize_embeddings=True,
            )
            return self._normalize(vectors[0].tolist())

        inputs = processor_or_none(text=[text or ""], return_tensors="pt", padding=True, truncation=True)
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch_or_none.no_grad():
            features = model.get_text_features(**inputs)
        return self._normalize(features[0].detach().cpu().tolist())

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return [self._embed_item(item) for item in texts]

    def get_config(self) -> Dict[str, Any]:
        provider = "huggingface_local_clip"
        if self.model_name.lower().startswith("qwen/qwen3-vl-embedding"):
            provider = "huggingface_local_qwen3_vl_embedding"

        return {
            "provider": provider,
            "model": self.model_name,
            "device": self.device,
            "supports": ["text_query", "image_uri"],
        }

    def _embed_item(self, item: str) -> List[float]:
        value = str(item or "")
        if value.startswith("image://"):
            return self._embed_image_uri(value)
        return self.embed_text(value)

    def _embed_image_uri(self, uri: str) -> List[float]:
        storage_key = uri[len("image://") :]
        image_bytes = get_file_storage().load(storage_key)
        backend, model, processor_or_none, torch_or_none = self._load_model()

        if backend == "qwen3_vl_st":
            # Qwen3-VL sentence-transformers backend accepts multimodal dict inputs.
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            try:
                with Image.open(io.BytesIO(image_bytes)) as image:
                    image.convert("RGB").save(tmp_path)
                vectors = model.encode(
                    [{"image": tmp_path}],
                    normalize_embeddings=True,
                )
                return self._normalize(vectors[0].tolist())
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        with Image.open(io.BytesIO(image_bytes)) as image:
            rgb_image = image.convert("RGB")
            inputs = processor_or_none(images=rgb_image, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch_or_none.no_grad():
            features = model.get_image_features(**inputs)
        return self._normalize(features[0].detach().cpu().tolist())

    def _load_model(self):
        cache_key = f"{self.model_name}:{self.device}"
        with _MODEL_CACHE_LOCK:
            cached = _MODEL_CACHE.get(cache_key)
        if cached is not None:
            return cached

        if self.model_name.lower().startswith("qwen/qwen3-vl-embedding"):
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "Qwen3-VL embedding requires sentence-transformers. "
                    "Install it and retry."
                ) from exc

            logger.info("Loading Qwen3-VL embedding model '%s' on %s", self.model_name, self.device)
            model = SentenceTransformer(
                self.model_name,
                trust_remote_code=True,
                device=self.device,
            )
            loaded = ("qwen3_vl_st", model, None, None)
            with _MODEL_CACHE_LOCK:
                _MODEL_CACHE.setdefault(cache_key, loaded)
                return _MODEL_CACHE[cache_key]

        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as exc:
            raise RuntimeError(
                "CLIP image indexing requires torch and transformers to be installed."
            ) from exc

        logger.info("Loading CLIP image embedding model '%s' on %s", self.model_name, self.device)
        processor = CLIPProcessor.from_pretrained(self.model_name)
        model = CLIPModel.from_pretrained(self.model_name)
        model.to(self.device)
        model.eval()

        loaded = ("clip", model, processor, torch)
        with _MODEL_CACHE_LOCK:
            _MODEL_CACHE.setdefault(cache_key, loaded)
            return _MODEL_CACHE[cache_key]

    @staticmethod
    def _normalize(vector: List[float]) -> List[float]:
        norm = sum(float(value) * float(value) for value in vector) ** 0.5
        if norm == 0:
            return [float(value) for value in vector]
        return [float(value) / norm for value in vector]
