from __future__ import annotations

import hashlib
import math
from functools import cached_property

import numpy as np

from app.config import get_settings


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @cached_property
    def model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.settings.embedding_model, device=self.settings.embedding_device)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        cleaned = [text.strip() for text in texts if text and text.strip()]
        if not cleaned:
            return []
        try:
            embeddings = self.model.encode(
                cleaned,
                normalize_embeddings=self.settings.embedding_normalize,
                batch_size=self.settings.embedding_batch_size,
                convert_to_numpy=True,
            )
            return np.asarray(embeddings, dtype=np.float32).tolist()
        except Exception:
            # Deterministic semantic fallback if model weights are not yet available.
            return [self._hash_embedding(text) for text in cleaned]

    def embed_text(self, text: str) -> list[float]:
        embedded = self.embed_texts([text])
        if not embedded:
            return [0.0] * self.settings.embedding_dimension
        return embedded[0]

    def _hash_embedding(self, text: str) -> list[float]:
        dim = self.settings.embedding_dimension
        vector = np.zeros(dim, dtype=np.float32)
        tokens = [token.lower() for token in text.split()]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for idx in range(0, len(digest), 2):
                bucket = int.from_bytes(digest[idx : idx + 2], "big") % dim
                vector[bucket] += 1.0
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector.tolist()


embedding_service = EmbeddingService()


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    a = np.asarray(vec_a, dtype=np.float32)
    b = np.asarray(vec_b, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    value = float(np.dot(a, b) / denom)
    return max(min(value, 1.0), -1.0)


def normalize_similarity_to_score(similarity: float) -> int:
    bounded = max(min(similarity, 1.0), -1.0)
    return int(round(((bounded + 1.0) / 2.0) * 100))


def km_to_minutes(distance_km: float, kmh: float) -> int:
    if kmh <= 0:
        return 0
    hours = distance_km / kmh
    return max(1, int(math.ceil(hours * 60)))
