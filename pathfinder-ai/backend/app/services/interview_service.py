"""AI Interview Mode sessions."""
from __future__ import annotations

import random

from sqlalchemy.orm import Session

from app.ai.interview import evaluate
from app.core.errors import AppError, NotFound
from app.db.models import ChatMessage, ChatSession, Progress, User
from app.knowledge.catalog import Catalog
from app.services.profile_service import get_or_create_profile

MODES = {"technical": "Technical Interview", "behavioral": "Behavioral Interview", "case_study": "Case Study",
         "system_design": "System Design", "sql": "SQL", "coding": "Coding", "domain": "Domain Knowledge"}
MAX_QUESTIONS = 5


def _select_questions(catalog: Catalog, career_id: str, mode: str) -> list[str]:
    career = catalog.careers[career_id]
    weight = {r.skill_id: {"core": 3, "important": 2, "useful": 1}[r.importance] for r in career.skills}
    pool = [q for q in catalog.questions.values() if q.mode == mode]
    if mode != "behavioral":
        scored = [(sum(weight.get(s, 0) for s in q.skills), q.id) for q in pool]
        relevant = [qid for score, qid in sorted(scored, key=lambda t: -t[0]) if score > 0]
        if relevant:
            return relevant[:MAX_QUESTIONS]
        # Nothing mode-specific for this career: fall back to its technical/domain questions.
        alt = [q for q in catalog.questions.values() if q.mode in ("technical", "domain") and set(q.skills) & set(weight)]
        return [q.id for q in sorted(alt, key=lambda q: -sum(weight.get(s, 0) for s in q.skills))][:MAX_QUESTIONS]
    ids = [q.id for q in pool]
    random.Random(career_id).shuffle(ids)
    return ids[:MAX_QUESTIONS]


def start(db: Session, user: User, catalog: Catalog, *, career_id: str | None, mode: str) -> dict:
    profile = get_or_create_profile(db, user)
    career_id = career_id or profile.target_career_id
    if not career_id or career_id not in catalog.careers:
        raise AppError("Pick a career to practise for.", code="no_target_career")
    queue = _select_questions(catalog, career_id, mode)
    if not queue:
        raise NotFound("We don't have questions for that mode yet.")
    career = catalog.careers[career_id]
    session = ChatSession(user_id=user.id, kind="interview", title=f"{career.name} · {MODES[mode]}",
                          meta={"career_id": career_id, "mode": mode, "queue": queue, "index": 0, "current": queue[0],
                                "follow_up": None, "results": []})
    db.add(session)
    db.flush()
    q = catalog.questions[queue[0]]
    db.add(ChatMessage(session_id=session.id, role="assistant", content=q.prompt, meta={"question_id": q.id}))
    db.commit()
    return {"session_id": session.id, "title": session.title, "career_name": career.name, "mode": mode, "mode_label": MODES[mode],
            "question": {"id": q.id, "prompt": q.prompt, "number": 1, "total": len(queue), "is_follow_up": False}}


async def answer(db: Session, user: User, catalog: Catalog, *, session_id: str, text: str) -> dict:
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id or session.kind != "interview":
        raise NotFound("Interview session not found.")
    meta = dict(session.meta)
    if meta.get("finished"):
        raise AppError("This interview is complete. Start a new one to keep practising.", code="interview_finished")
    q = catalog.questions[meta["current"]]
    career = catalog.careers[meta["career_id"]]
    db.add(ChatMessage(session_id=session.id, role="user", content=text))
    result = await evaluate(q, text, career.name)
    is_follow_up = bool(meta.get("follow_up"))
    meta["results"] = [*meta["results"], {"question_id": q.id, "follow_up": is_follow_up, "coverage": result["technical_coverage"],
                                          "clarity": result["clarity"]}]

    if result["technical_coverage"] >= 70 and q.skills and not is_follow_up:
        db.add(Progress(user_id=user.id, kind="assessment", ref_id=q.id, skill_ids=q.skills,
                        title=f"Interview practice: {q.prompt[:80]}", detail=f"Covered {result['technical_coverage']}% of key concepts"))

    # Next: one follow-up on the same topic if concepts were missed, then move on.
    next_q = None
    if not is_follow_up and result["missing_concepts"] and q.follow_ups:
        prompt = result.get("ai_follow_up") or q.follow_ups[0]
        meta["follow_up"] = prompt
        next_q = {"id": q.id, "prompt": prompt, "is_follow_up": True}
    else:
        meta["follow_up"] = None
        meta["index"] += 1
        if meta["index"] < len(meta["queue"]):
            meta["current"] = meta["queue"][meta["index"]]
            nq = catalog.questions[meta["current"]]
            next_q = {"id": nq.id, "prompt": nq.prompt, "is_follow_up": False}
        else:
            meta["finished"] = True
    if next_q:
        next_q.update({"number": meta["index"] + 1, "total": len(meta["queue"])})
        db.add(ChatMessage(session_id=session.id, role="assistant", content=next_q["prompt"], meta={"question_id": next_q["id"]}))
    session.meta = meta
    db.commit()
    return {"evaluation": result, "next_question": next_q, "finished": bool(meta.get("finished")),
            "summary": _summary(meta) if meta.get("finished") else None}


def _summary(meta: dict) -> dict:
    rs = meta["results"]
    cov = round(sum(r["coverage"] for r in rs) / len(rs)) if rs else 0
    clar = round(sum(r["clarity"] for r in rs) / len(rs)) if rs else 0
    return {"questions_answered": len(rs), "avg_coverage": cov, "avg_clarity": clar,
            "note": "Practice scores reflect concept coverage in your answers — they're a study aid, not a hiring prediction."}
