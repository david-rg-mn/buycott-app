import hashlib
import logging
import re
from functools import lru_cache
from threading import Lock
from typing import Iterable

import numpy as np

from ..config import settings

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-z0-9]+")


class EmbeddingService:
    """Embedding provider with model-first and deterministic fallback behavior."""

    def __init__(self) -> None:
        self._model = None
        self._model_failed = False
        self._model_lock = Lock()

    def _load_model(self):
        if not settings.enable_model_embeddings or self._model_failed:
            return None
        with self._model_lock:
            if self._model is not None:
                return self._model
            if self._model_failed:
                return None

            try:
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer(settings.embedding_model_name, device="cpu")
                # Preflight a tiny encode to ensure model tensors are materialized correctly.
                _ = model.encode(["healthcheck"], normalize_embeddings=True)
                self._model = model
                logger.info("Loaded embedding model: %s", settings.embedding_model_name)
            except Exception as exc:  # pragma: no cover - depends on runtime availability
                self._model_failed = True
                logger.warning("Falling back to deterministic embeddings: %s", exc)
                self._model = None
        return self._model

    def _mark_model_failed(self, exc: Exception) -> None:
        with self._model_lock:
            self._model_failed = True
            self._model = None
        logger.warning("Embedding model inference failed; using deterministic fallback: %s", exc)

    def _hash_embed(self, text: str) -> list[float]:
        dim = settings.embedding_dimension
        vec = np.zeros(dim, dtype=np.float32)
        tokens = TOKEN_RE.findall(text.lower())
        if not tokens:
            tokens = [text.lower().strip() or "empty"]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for idx in range(0, len(digest), 2):
                bucket = ((digest[idx] << 8) + digest[idx + 1]) % dim
                signed = 1.0 if digest[idx] % 2 == 0 else -1.0
                weight = 0.5 + (digest[idx + 1] / 255.0)
                vec[bucket] += signed * weight

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.astype(np.float32).tolist()

    def encode(self, text: str) -> list[float]:
        model = self._load_model()
        if model is not None:
            try:
                vector = model.encode(text, normalize_embeddings=True)
                if hasattr(vector, "tolist"):
                    return vector.tolist()
                return list(vector)
            except Exception as exc:  # pragma: no cover - runtime dependent
                self._mark_model_failed(exc)
        return self._hash_embed(text)

    def encode_many(self, texts: Iterable[str]) -> list[list[float]]:
        text_list = list(texts)
        if not text_list:
            return []

        model = self._load_model()
        if model is not None:
            try:
                matrix = model.encode(text_list, normalize_embeddings=True)
                return [row.tolist() if hasattr(row, "tolist") else list(row) for row in matrix]
            except Exception as exc:  # pragma: no cover - runtime dependent
                self._mark_model_failed(exc)
        return [self._hash_embed(text) for text in text_list]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
