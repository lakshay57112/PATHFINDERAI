"""Mentor, interview, job-market, search, account and system endpoints."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm import get_llm
from app.api.deps import catalog_dep, current_user, rate_limit
from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.errors import AppError, NotFound
from app.db.models import ChatSession, JobMarketData, Progress, Roadmap, User
from app.db.session import SessionLocal, get_db
from app.graphdb.store import get_graph
from app.knowledge.catalog import Catalog
from app.rag.retriever import get_retriever, retrieval_config
from app.schemas.api import InterviewAnswerIn, InterviewStartIn, MarketAnalyzeIn, MarketIngestIn, MentorChatIn
from app.services import interview_service, market_service, mentor_service, storage
from app.services.profile_service import build_snapshot, serialize_profile
from app.workers.celery_app import celery_app, run_task
from app.workers.tasks import ingest_postings

router = APIRouter()


# ------------------------------------------------------------------------ mentor
@router.post("/mentor/chat", tags=["mentor"], dependencies=[Depends(rate_limit("mentor"))])
async def mentor_chat(data: MentorChatIn, user: User = Depends(current_user)):
    user_id = user.id

    async def stream():
        # The stream owns its own DB session so it stays valid for the whole response.
        with SessionLocal() as db:
            u = db.get(User, user_id)
            try:
                async for chunk in mentor_service.chat_stream(db, u, catalog_dep(), data.message, data.session_id):
                    yield chunk
            except AppError as exc:
                yield f"event: error\ndata: {json.dumps({'code': exc.code, 'message': exc.message})}\n\n"
            except Exception:
                yield f"event: error\ndata: {json.dumps({'code': 'internal_error', 'message': 'The mentor hit a problem. Please try again.'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/mentor/suggestions", tags=["mentor"])
def mentor_suggestions():
    return {"suggestions": mentor_service.SUGGESTIONS}


@router.get("/mentor/sessions", tags=["mentor"])
def mentor_sessions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return mentor_service.list_sessions(db, user)


@router.get("/mentor/sessions/{session_id}", tags=["mentor"])
def mentor_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return mentor_service.session_messages(db, user, session_id)


# ------------------------------------------------------------------------ interview
@router.get("/interview/modes", tags=["interview"])
def interview_modes():
    return [{"id": k, "label": v} for k, v in interview_service.MODES.items()]


@router.post("/interview/start", tags=["interview"], dependencies=[Depends(rate_limit("interview"))])
def interview_start(data: InterviewStartIn, user: User = Depends(current_user), db: Session = Depends(get_db),
                    catalog: Catalog = Depends(catalog_dep)):
    return interview_service.start(db, user, catalog, career_id=data.career_id, mode=data.mode)


@router.post("/interview/answer", tags=["interview"], dependencies=[Depends(rate_limit("interview"))])
async def interview_answer(data: InterviewAnswerIn, user: User = Depends(current_user), db: Session = Depends(get_db),
                           catalog: Catalog = Depends(catalog_dep)):
    return await interview_service.answer(db, user, catalog, session_id=data.session_id, text=data.answer)


# ------------------------------------------------------------------------ job market
@router.get("/market/options", tags=["market"])
def market_options(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return market_service.options(db, user)


@router.post("/market/analyze", tags=["market"])
def market_analyze(data: MarketAnalyzeIn, user: User = Depends(current_user), db: Session = Depends(get_db),
                   catalog: Catalog = Depends(catalog_dep)):
    if data.career_id not in catalog.careers:
        raise NotFound("Career not found.")
    snap = build_snapshot(db, user, catalog)
    return market_service.analyze(db, user, catalog, career_id=data.career_id, country=data.country, city=data.city,
                                  remote=data.remote, industry=data.industry, include_synthetic=data.include_synthetic,
                                  user_skills={k: v.level for k, v in snap.skills.items()})


@router.post("/market/ingest", tags=["market"], dependencies=[Depends(rate_limit("ingest", 10))])
def market_ingest(data: MarketIngestIn, user: User = Depends(current_user), catalog: Catalog = Depends(catalog_dep)):
    if data.career_id and data.career_id not in catalog.careers:
        raise NotFound("Career not found.")
    postings = [p.model_dump(mode="json") for p in data.postings]
    return run_task(ingest_postings, user.id, data.source, data.career_id, postings)


@router.get("/tasks/{task_id}", tags=["system"])
def task_status(task_id: str, _: User = Depends(current_user)):
    res = celery_app.AsyncResult(task_id)
    state = res.state.lower()
    return {"task_id": task_id, "status": "completed" if state == "success" else state,
            "result": res.result if res.successful() else None}


# ------------------------------------------------------------------------ search
@router.get("/search", tags=["knowledge"], dependencies=[Depends(rate_limit("search", 60))])
def search(q: str = Query(min_length=2, max_length=200), type: str | None = None, k: int = Query(5, ge=1, le=10)):
    key = f"search:{type}:{k}:{q.lower()}"
    if cached := get_cache().get_json(key):
        return cached
    out = {"query": q, "results": get_retriever().search(q, k=k, types=[type] if type else None), **retrieval_config()}
    get_cache().set_json(key, out, ttl=600)
    return out


# ------------------------------------------------------------------------ account / privacy
@router.get("/account/export", tags=["account"])
def export_account(user: User = Depends(current_user), db: Session = Depends(get_db), catalog: Catalog = Depends(catalog_dep)):
    from app.services.roadmap_service import serialize_roadmap

    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": serialize_profile(user, catalog),
        "roadmaps": [serialize_roadmap(r, catalog) for r in db.scalars(select(Roadmap).where(Roadmap.user_id == user.id))],
        "evidence": [{"kind": p.kind, "title": p.title, "detail": p.detail, "url": p.url, "created_at": p.created_at.isoformat()}
                     for p in db.scalars(select(Progress).where(Progress.user_id == user.id))],
        "conversations": [{"kind": s.kind, "title": s.title, "created_at": s.created_at.isoformat(),
                           "messages": [{"role": m.role, "content": m.content} for m in s.messages]}
                          for s in db.scalars(select(ChatSession).where(ChatSession.user_id == user.id))],
        "job_postings_you_added": [{"title": j.title, "source": j.source} for j in
                                   db.scalars(select(JobMarketData).where(JobMarketData.owner_id == user.id))],
    }
    return JSONResponse(data, headers={"Content-Disposition": 'attachment; filename="pathfinder-export.json"'})


@router.delete("/account", tags=["account"])
def delete_account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.is_demo:
        raise AppError("The shared demo account can't be deleted.", code="demo_account", status_code=403)
    for c in user.certificates:
        storage.delete(c.file_key)
    db.query(JobMarketData).filter(JobMarketData.owner_id == user.id).delete()
    db.delete(user)
    db.commit()
    resp = JSONResponse({"ok": True, "message": "Your account and all associated data were deleted."})
    resp.delete_cookie("pf_session", path="/")
    return resp


# ------------------------------------------------------------------------ system
@router.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@router.get("/system/status", tags=["system"])
def system_status():
    s = get_settings()
    llm = get_llm()
    try:
        rag = retrieval_config()
    except Exception:
        rag = {"status": "unavailable"}
    return {
        "ai": {"provider": llm.provider, "model": llm.model_name, "available": llm.available},
        "database": "sqlite" if s.is_sqlite else "postgresql",
        "cache": get_cache().backend,
        "rag": rag,
        "graph": get_graph().backend,
        "background_jobs": "inline" if celery_app.conf.task_always_eager else "celery",
    }
