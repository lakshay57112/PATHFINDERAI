"""Background jobs."""
from __future__ import annotations

from app.db.models import User
from app.db.session import SessionLocal
from app.knowledge.catalog import get_catalog
from app.services import market_service
from app.workers.celery_app import celery_app


@celery_app.task(name="market.ingest_postings", bind=True, max_retries=2, default_retry_delay=10)
def ingest_postings(self, user_id: str, source: str, career_id: str | None, postings: list[dict]) -> dict:
    from datetime import date

    for p in postings:
        if isinstance(p.get("posted_on"), str):
            p["posted_on"] = date.fromisoformat(p["posted_on"])
    with SessionLocal() as db:
        user = db.get(User, user_id)
        n = market_service.ingest(db, user, get_catalog(), source=source, career_id=career_id, postings=postings)
    return {"ingested": n}


@celery_app.task(name="knowledge.reindex")
def reindex_knowledge() -> dict:
    from app.rag.documents import build_documents
    from app.rag.retriever import get_retriever

    n = get_retriever().index(build_documents(get_catalog()))
    return {"documents": n}
