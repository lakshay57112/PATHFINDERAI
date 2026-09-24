"""Embedding providers.

* openai       – text-embedding-3-small (needs OPENAI_API_KEY)
* huggingface  – fastembed / sentence-transformers model, if installed
* hash         – deterministic feature-hashing embedder (no downloads, used offline & in tests)
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings

log = logging.getLogger("pathfinder.embeddings")
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")


def tokenize(text: str) -> list[str]:
    return [t.strip(".-") for t in TOKEN_RE.findall(text.lower()) if t.strip(".-")]


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    """Signed feature hashing over unigrams, bigrams and character trigrams, L2-normalised."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.name = f"hash-{dim}"

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        toks = tokenize(text)
        feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        for t in toks:
            padded = f"#{t}#"
            feats += [padded[i:i + 3] for i in range(len(padded) - 2)]
        for f in feats:
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "little")
            idx, sign = h % self.dim, 1.0 if (h >> 63) & 1 else -1.0
            weight = 1.0 if "_" not in f and len(f) > 3 else 0.5
            v[idx] += sign * weight
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


class OpenAIEmbedder:
    def __init__(self) -> None:
        from openai import OpenAI

        s = get_settings()
        self.client = OpenAI(api_key=s.openai_api_key, timeout=30)
        self.model = s.openai_embedding_model
        self.name = self.model
        self.dim = 1536 if "small" in self.model else 3072

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 256):
            resp = self.client.embeddings.create(model=self.model, input=texts[i:i + 256])
            out.extend(d.embedding for d in resp.data)
        return out


class HFEmbedder:
    def __init__(self) -> None:
        from fastembed import TextEmbedding  # optional dependency

        model = get_settings().hf_embedding_model
        self.model = TextEmbedding(model_name=model)
        self.name = model
        self.dim = len(next(iter(self.model.embed(["probe"]))))

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self.model.embed(texts)]


@lru_cache
def get_embedder() -> Embedder:
    s = get_settings()
    choice = s.embedding_provider
    if choice in ("openai", "auto") and s.openai_api_key:
        try:
            return OpenAIEmbedder()
        except Exception as exc:  # pragma: no cover - depends on network/keys
            log.warning("OpenAI embeddings unavailable (%s)", exc)
    if choice in ("huggingface", "auto"):
        try:
            return HFEmbedder()
        except Exception as exc:
            if choice == "huggingface":
                log.warning("Hugging Face embeddings unavailable (%s); using hash embeddings", exc)
    return HashEmbedder()
