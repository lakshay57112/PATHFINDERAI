"""Progress tracking: completion across skills, projects and phases, plus the evidence log."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Progress, User
from app.engines.readiness import readiness
from app.knowledge.catalog import Catalog
from app.services.profile_service import build_snapshot
from app.services.roadmap_service import active_roadmap, next_step, serialize_roadmap

EVIDENCE_LABELS = {"skill": "Roadmap skill", "project": "Project", "certificate": "Certificate", "assessment": "Assessment",
                   "quiz": "Quiz", "artifact": "Portfolio artifact"}


def progress_overview(db: Session, user: User, catalog: Catalog) -> dict:
    rm = active_roadmap(db, user)
    evidence = db.scalars(select(Progress).where(Progress.user_id == user.id).order_by(Progress.created_at.desc()).limit(50)).all()
    ev = [{"id": e.id, "kind": e.kind, "label": EVIDENCE_LABELS.get(e.kind, e.kind), "title": e.title, "detail": e.detail, "url": e.url,
           "skills": [catalog.skill_name(s) for s in (e.skill_ids or [])], "created_at": e.created_at.isoformat()} for e in evidence]
    if not rm:
        return {"has_roadmap": False, "evidence": ev}

    data = serialize_roadmap(rm, catalog)
    steps = [s for ph in data["phases"] for s in ph["steps"] if not s["optional"]]
    finished = lambda s: s["status"] in ("done", "skipped")
    skill_steps = [s for s in steps if s["kind"] == "skill"]
    project_steps = [s for s in steps if s["kind"] == "project"]
    user_projects_done = [p for p in user.projects if p.status == "completed"]
    phases_real = [ph for ph in data["phases"] if ph["steps"]]
    total_h = sum(s["est_hours"] for s in steps) or 1
    done_h = sum(s["est_hours"] for s in steps if finished(s))
    snap = build_snapshot(db, user, catalog)
    career = catalog.careers[rm.career_id]
    return {
        "has_roadmap": True,
        "career_id": rm.career_id,
        "career_name": data["career_name"],
        "overall": round(done_h / total_h, 3),
        "overall_basis": "Share of estimated roadmap hours completed",
        "skills": {"done": sum(finished(s) for s in skill_steps), "total": len(skill_steps)},
        "projects": {"done": sum(finished(s) for s in project_steps) + len(user_projects_done),
                     "total": len(project_steps) + len(user_projects_done)},
        "phases": {"done": sum(ph["status"] == "done" for ph in phases_real), "total": len(phases_real)},
        "phase_progress": [{"name": ph["name"], "progress": ph["progress"], "status": ph["status"]} for ph in data["phases"]],
        "next_step": next_step(data),
        "remaining_label": data["remaining_label"],
        "evidence": ev,
        "readiness": readiness(snap, career, catalog),
    }
