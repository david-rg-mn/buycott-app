from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable, Mapping

import numpy as np

TOKEN_RE = re.compile(r"[a-z0-9]+")


def accent_fold(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    folded = accent_fold(text)
    cleaned = re.sub(r"[^a-z0-9\\s]", " ", folded)
    return " ".join(cleaned.split())


def singularize(token: str) -> str:
    if len(token) <= 3:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    tokens = TOKEN_RE.findall(normalized)
    if not tokens:
        return []
    output: list[str] = []
    for token in tokens:
        output.append(token)
        singular = singularize(token)
        if singular != token:
            output.append(singular)
    return output


def ngrams(tokens: list[str], min_n: int = 1, max_n: int = 4) -> list[str]:
    if not tokens:
        return []
    max_width = max(min_n, min(max_n, len(tokens)))
    output: list[str] = []
    for width in range(min_n, max_width + 1):
        for start in range(0, len(tokens) - width + 1):
            output.append(" ".join(tokens[start : start + width]))
    return output


class DeterministicVectorizer:
    """Deterministic concept hashing for Phase A (no ML inference)."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def encode_weighted_terms(self, weighted_terms: Mapping[str, float]) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        for term, weight in weighted_terms.items():
            normalized = normalize_text(term)
            if not normalized:
                continue
            digest = hashlib.sha256(normalized.encode("utf-8")).digest()
            for idx in range(0, len(digest), 2):
                bucket = ((digest[idx] << 8) + digest[idx + 1]) % self.dim
                signed = 1.0 if digest[idx] % 2 == 0 else -1.0
                vec[bucket] += signed * float(weight)

        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec.astype(np.float32).tolist()

    def encode_terms(self, terms: Iterable[str]) -> list[float]:
        weighted = {term: 1.0 for term in terms}
        return self.encode_weighted_terms(weighted)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    arr_a = np.array(vec_a, dtype=np.float32)
    arr_b = np.array(vec_b, dtype=np.float32)
    denom = float(np.linalg.norm(arr_a) * np.linalg.norm(arr_b))
    if denom <= 0:
        return 0.0
    return float(np.dot(arr_a, arr_b) / denom)
