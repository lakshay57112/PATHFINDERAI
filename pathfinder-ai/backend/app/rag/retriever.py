"""Hybrid retrieval: Qdrant dense search + BM25 sparse search, fused with Reciprocal Rank
Fusion and reranked (cross-encoder when configured, lexical reranker otherwise).
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.core.errors import AppError
from app.knowledge.catalog import get_catalog
from app.rag.documents import KBDocument, build_documents
from app.rag.embeddings import Embedder, get_embedder, tokenize

log = logging.getLogger("pathfinder.rag")
RRF_K = 60
STOPWORDS = {"the", "a", "an", "and", "or", "of", "to", "in", "for", "is", "what", "how", "do", "i", "me", "my", "it", "on",
             "with", "should", "does", "are", "be", "can", "you", "your", "this", "that", "as", "at", "by", "from", "about"}


def rrf(rankings: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


class LexicalReranker:
    name = "lexical"

    def score(self, query: str, docs: list[KBDocument]) -> list[float]:
        q = {t for t in tokenize(query) if t not in STOPWORDS}
        out = []
        for d in docs:
            title = set(tokenize(d.title))
            body = set(tokenize(d.text))
            out.append((2.0 * len(q & title) + len(q & body)) / (len(q) or 1))
        return out


class CrossEncoderReranker:  # pragma: no cover - optional heavy dependency
    def __init__(self, model: str) -> None:
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model)
        self.name = model

    def score(self, query: str, docs: list[KBDocument]) -> list[float]:
        return [float(s) for s in self.model.predict([(query, d.text) for d in docs])]


class HybridRetriever:
    def __init__(self, embedder: Embedder | None = None) -> None:
        s = get_settings()
        self.embedder = embedder or get_embedder()
        self.collection = f"{s.qdrant_collection}_{self.embedder.name.replace('/', '_').replace('.', '_')}"
        self.client = self._client()
        self.docs: dict[str, KBDocument] = {}
        self.ids: list[str] = []
        self.bm25: BM25Okapi | None = None
        self.reranker = self._reranker()
        self._lock = threading.Lock()

    @staticmethod
    def _client() -> QdrantClient:
        s = get_settings()
        if s.qdrant_url:
            try:
                client = QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key, timeout=5)
                client.get_collections()
                return client
            except Exception as exc:
                log.warning("Qdrant at %s unavailable (%s); using embedded in-memory Qdrant", s.qdrant_url, exc)
        return QdrantClient(location=":memory:")

    @staticmethod
    def _reranker():
        model = get_settings().reranker_model
        if model:
            try:
                return CrossEncoderReranker(model)
            except Exception as exc:
                log.warning("Cross-encoder %s unavailable (%s); using lexical reranker", model, exc)
        return LexicalReranker()

    @property
    def backend(self) -> str:
        return "qdrant-server" if get_settings().qdrant_url and "memory" not in str(self.client._client.__class__).lower() else "qdrant-embedded"

    def index(self, docs: list[KBDocument]) -> int:
        with self._lock:
            t0 = time.time()
            self.docs = {d.id: d for d in docs}
            self.ids = [d.id for d in docs]
            self.bm25 = BM25Okapi([tokenize(f"{d.title} {d.text}") for d in docs])
            vectors = self.embedder.embed([f"{d.title}. {d.text}" for d in docs])
            if self.client.collection_exists(self.collection):
                self.client.delete_collection(self.collection)
            self.client.create_collection(self.collection, vectors_config=qm.VectorParams(size=len(vectors[0]), distance=qm.Distance.COSINE))
            points = [
                qm.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, d.id)), vector=v,
                               payload={"doc_id": d.id, "type": d.type, **{k: v2 for k, v2 in d.metadata.items() if v2 is not None}})
                for d, v in zip(docs, vectors)
            ]
            for i in range(0, len(points), 256):
                self.client.upsert(self.collection, points=points[i:i + 256])
            log.info("indexed %d documents in %.1fs (embedder=%s)", len(docs), time.time() - t0, self.embedder.name)
            return len(docs)

    def _dense(self, query: str, k: int, types: list[str] | None) -> list[str]:
        vec = self.embedder.embed([query])[0]
        flt = qm.Filter(must=[qm.FieldCondition(key="type", match=qm.MatchAny(any=types))]) if types else None
        try:
            res = self.client.query_points(self.collection, query=vec, limit=k, query_filter=flt, with_payload=True).points
        except Exception as exc:
            log.warning("vector search failed: %s", exc)
            raise AppError("Knowledge search is temporarily unavailable.", code="vector_db_error", status_code=503) from exc
        return [p.payload["doc_id"] for p in res]

    def _sparse(self, query: str, k: int, types: list[str] | None) -> list[str]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])
        out = []
        for i in ranked:
            if scores[i] <= 0:
                break
            d = self.docs[self.ids[i]]
            if types and d.type not in types:
                continue
            out.append(d.id)
            if len(out) >= k:
                break
        return out

    def search(self, query: str, k: int = 5, types: list[str] | None = None, candidates: int = 20) -> list[dict]:
        if not self.docs:
            raise AppError("The knowledge base is still loading.", code="kb_not_ready", status_code=503)
        dense = self._dense(query, candidates, types)
        sparse = self._sparse(query, candidates, types)
        fused = rrf([dense, sparse])
        pool = sorted(fused, key=lambda d: -fused[d])[: max(k * 3, 15)]
        docs = [self.docs[d] for d in pool]
        rer = self.reranker.score(query, docs)
        # Blend reranker with fused rank so both retrieval signals still matter.
        max_r = max(rer) if rer and max(rer) > 0 else 1.0
        max_f = max(fused.values()) if fused else 1.0
        final = sorted(
            ((0.6 * (r / max_r) + 0.4 * (fused[d.id] / max_f), d) for r, d in zip(rer, docs)),
            key=lambda t: -t[0],
        )[:k]
        return [{"score": round(s, 4), "text": d.text, **d.citation(),
                 "signals": {"dense_rank": dense.index(d.id) + 1 if d.id in dense else None,
                             "bm25_rank": sparse.index(d.id) + 1 if d.id in sparse else None}}
                for s, d in final]


_retriever: HybridRetriever | None = None
_lock = threading.Lock()


def get_retriever() -> HybridRetriever:
    global _retriever
    with _lock:
        if _retriever is None:
            r = HybridRetriever()
            r.index(build_documents(get_catalog()))
            _retriever = r
    return _retriever


@lru_cache
def retrieval_config() -> dict:
    r = get_retriever()
    return {"embedder": r.embedder.name, "reranker": r.reranker.name, "documents": len(r.docs), "fusion": f"RRF (k={RRF_K})"}
