from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.pipeline import run_pipeline
from app.api.deps import catalog_dep, current_user, rate_limit
from app.core.errors import AppError, NotFound
from app.db.models import Recommendation, User
from app.db.session import get_db
from app.engines.readiness import readiness
from app.engines.recommendations import learning_plan_for_skill
from app.engines.skill_gap import analyze_gap
from app.knowledge.catalog import Catalog
from app.schemas.api import RecommendationsIn, RoadmapAdjustIn, RoadmapGenerateIn, StepUpdateIn
from app.services import roadmap_service as rs
from app.services.profile_service import build_snapshot, get_or_create_profile
from app.services.progress_service import progress_overview

router = APIRouter(tags=["planning"])


def _target(db: Session, user: User, catalog: Catalog, career_id: str | None):
    cid = career_id or get_or_create_profile(db, user).target_career_id
    if not cid:
        raise AppError("Choose a target career first.", code="no_target_career")
    if cid not in catalog.careers:
        raise NotFound("Career not found.")
    return catalog.careers[cid]


@router.get("/gap-analysis")
def gap_analysis(career_id: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db),
                 catalog: Catalog = Depends(catalog_dep)):
    career = _target(db, user, catalog, career_id)
    return analyze_gap(build_snapshot(db, user, catalog), career, catalog)


@router.get("/readiness")
def get_readiness(career_id: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db),
                  catalog: Catalog = Depends(catalog_dep)):
    career = _target(db, user, catalog, career_id)
    return readiness(build_snapshot(db, user, catalog), career, catalog)


@router.post("/recommendations", dependencies=[Depends(rate_limit("recommend"))])
async def generate_recommendations(data: RecommendationsIn | None = None, user: User = Depends(current_user),
                                   db: Session = Depends(get_db), catalog: Catalog = Depends(catalog_dep)):
    career = _target(db, user, catalog, data.career_id if data else None)
    state = await run_pipeline(build_snapshot(db, user, catalog), catalog, target_career_id=career.id, enrich=False)
    db.execute(delete(Recommendation).where(Recommendation.user_id == user.id, Recommendation.kind.in_(("certificate", "project", "resource"))))
    for c in state["certificates"]["recommendations"]:
        db.add(Recommendation(user_id=user.id, kind="certificate", ref_id=c["id"], payload=c))
    for p in state["projects"]["projects"]:
        db.add(Recommendation(user_id=user.id, kind="project", ref_id=p["id"], payload=p))
    for r in state["learning"]:
        db.add(Recommendation(user_id=user.id, kind="resource", ref_id=r["skill_id"], payload=r))
    db.commit()
    return _recs_payload(career, state["certificates"], state["projects"], state["learning"], state["trace"])


def _recs_payload(career, certs, projects, learning, trace=None) -> dict:
    return {"career_id": career.id, "career_name": career.name, "certificates": certs, "projects": projects,
            "learning": learning, "trace": trace or []}


@router.get("/recommendations")
async def get_recommendations(user: User = Depends(current_user), db: Session = Depends(get_db),
                              catalog: Catalog = Depends(catalog_dep)):
    career = _target(db, user, catalog, None)
    rows = db.scalars(select(Recommendation).where(Recommendation.user_id == user.id, Recommendation.dismissed.is_(False))).all()
    if not any(r.kind == "project" for r in rows):
        return await generate_recommendations(None, user, db, catalog)
    snap = build_snapshot(db, user, catalog)
    gap = analyze_gap(snap, career, catalog)
    from app.engines.recommendations import recommend_certificates

    certs = recommend_certificates(snap, career, gap, catalog)  # cheap; keeps "existing" section fresh
    projects = [r.payload for r in rows if r.kind == "project"]
    start = next((p["difficulty"] for p in projects if p.get("suggested_start")), None)
    return _recs_payload(career, certs, {"projects": projects, "suggested_start": start, "flagship": projects[-1] if projects else None},
                         [r.payload for r in rows if r.kind == "resource"])


@router.post("/roadmap/generate", dependencies=[Depends(rate_limit("roadmap"))])
def roadmap_generate(data: RoadmapGenerateIn | None = None, user: User = Depends(current_user), db: Session = Depends(get_db),
                     catalog: Catalog = Depends(catalog_dep)):
    return rs.generate_roadmap(db, user, catalog, career_id=data.career_id if data else None,
                               hours_per_week=data.hours_per_week if data else None)


@router.get("/roadmap")
def roadmap_get(user: User = Depends(current_user), db: Session = Depends(get_db), catalog: Catalog = Depends(catalog_dep)):
    rm = rs.active_roadmap(db, user)
    if not rm:
        raise NotFound("You don't have a roadmap yet.")
    return rs.serialize_roadmap(rm, catalog)


@router.patch("/roadmap/steps/{step_id}")
def roadmap_step(step_id: str, data: StepUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db),
                 catalog: Catalog = Depends(catalog_dep)):
    return rs.update_step(db, user, step_id, data.status, catalog, evidence_url=str(data.evidence_url) if data.evidence_url else None,
                          note=data.note)


@router.post("/roadmap/adjust")
def roadmap_adjust(data: RoadmapAdjustIn, user: User = Depends(current_user), db: Session = Depends(get_db),
                   catalog: Catalog = Depends(catalog_dep)):
    result = None
    applied: list[str] = []
    if data.known_skills:
        unknown = [s for s in data.known_skills if s not in catalog.skills]
        if unknown:
            raise NotFound(f"Unknown skills: {', '.join(unknown)}")
        result, applied = rs.mark_known(db, user, data.known_skills, catalog)
    if data.hours_per_week:
        result = rs.set_hours(db, user, data.hours_per_week, catalog)
    if result is None:
        rm = rs.active_roadmap(db, user)
        if not rm:
            raise NotFound("You don't have a roadmap yet.")
        result = rs.serialize_roadmap(rm, catalog)
    return {**result, "applied_known": applied}


@router.get("/learning")
def learning(user: User = Depends(current_user), db: Session = Depends(get_db), catalog: Catalog = Depends(catalog_dep)):
    rm = rs.active_roadmap(db, user)
    if not rm:
        raise NotFound("Generate a roadmap to see your learning plan.")
    data = rs.serialize_roadmap(rm, catalog)
    career = catalog.careers[rm.career_id]
    items = []
    for ph in data["phases"]:
        for st in ph["steps"]:
            if st["kind"] != "skill":
                continue
            plan = learning_plan_for_skill(st["skill_id"], catalog, from_level=st["from_level"], to_level=st["target_level"], career=career)
            items.append({**plan, "phase": ph["name"], "status": st["status"], "step_id": st["id"], "optional": st["optional"]})
    return {"career_name": data["career_name"], "items": items,
            "principle": "Learn → Practice → Build → Prove. Evidence you can show beats certificates you can list."}


@router.get("/progress")
def progress(user: User = Depends(current_user), db: Session = Depends(get_db), catalog: Catalog = Depends(catalog_dep)):
    return progress_overview(db, user, catalog)


@router.get("/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db), catalog: Catalog = Depends(catalog_dep)):
    from app.engines.recommendations import recommend_certificates, recommend_projects

    profile = get_or_create_profile(db, user)
    out: dict = {"name": user.name, "onboarding_completed": profile.onboarding_completed, "target": None}
    cid = profile.target_career_id
    if not cid or cid not in catalog.careers:
        return out
    career = catalog.careers[cid]
    snap = build_snapshot(db, user, catalog)
    gap = analyze_gap(snap, career, catalog)
    projects = recommend_projects(snap, career, gap, catalog)
    certs = recommend_certificates(snap, career, gap, catalog)
    prog = progress_overview(db, user, catalog)
    rec_project = next((p for p in projects["projects"] if p.get("suggested_start")), None) or (projects["projects"][0] if projects["projects"] else None)
    out.update({
        "target": {"id": career.id, "name": career.name},
        "progress": prog.get("overall") if prog.get("has_roadmap") else None,
        "has_roadmap": prog.get("has_roadmap", False),
        "next_step": prog.get("next_step"),
        "recommended_project": rec_project and {"id": rec_project["id"], "name": rec_project["name"], "difficulty": rec_project["difficulty"]},
        "insights": {
            "skills_to_develop": len([i for i in gap["items"] if i["status"] != "strong" and i["importance"] != "useful"]),
            "projects_recommended": len(projects["projects"]),
            "certificates_worth_exploring": len([c for c in certs["recommendations"] if c["verdict"] == "worth_exploring"]),
        },
        "readiness_next_step": prog.get("readiness", {}).get("next_step"),
        "phase_progress": prog.get("phase_progress", []),
        "recent_evidence": prog.get("evidence", [])[:4],
        "remaining_label": prog.get("remaining_label"),
    })
    return out
