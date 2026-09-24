"""Persistence + adaptive behaviour for roadmaps.

Adaptive rules:
  * completing a step raises the user's skill to the step's target and logs evidence
  * "I already know X" skips X's step and records the level (never re-taught later)
  * changing hours/week re-times the remaining plan
  * switching careers archives the current roadmap and builds a new one from the
    *updated* profile, so completed work carries over instead of starting from zero
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFound
from app.db.models import Progress, Project, Roadmap, RoadmapStep, User, UserSkill
from app.engines.recommendations import recommend_projects
from app.engines.roadmap import build_roadmap, summarize, weeks_range
from app.engines.skill_gap import analyze_gap
from app.knowledge.catalog import Catalog
from app.services.profile_service import build_snapshot, get_or_create_profile


def active_roadmap(db: Session, user: User) -> Roadmap | None:
    return db.scalars(
        select(Roadmap).where(Roadmap.user_id == user.id, Roadmap.status == "active").order_by(Roadmap.generated_at.desc())
    ).first()


def _career(catalog: Catalog, career_id: str):
    if career_id not in catalog.careers:
        raise NotFound("That career isn't in our knowledge base.")
    return catalog.careers[career_id]


def generate_roadmap(db: Session, user: User, catalog: Catalog, *, career_id: str | None = None,
                     hours_per_week: int | None = None) -> dict:
    profile = get_or_create_profile(db, user)
    career_id = career_id or profile.target_career_id
    if not career_id:
        raise AppError("Choose a target career before generating a roadmap.", code="no_target_career")
    career = _career(catalog, career_id)
    if hours_per_week:
        profile.hours_per_week = hours_per_week
    profile.target_career_id = career.id

    previous = active_roadmap(db, user)
    carried: list[str] = []
    switched_from = None
    if previous:
        done_skills = [s.skill_id for s in previous.steps if s.skill_id and s.status in ("done", "skipped")]
        carried = [catalog.skill_name(s) for s in done_skills if career.requirement(s)]
        if previous.career_id != career.id:
            switched_from = catalog.careers[previous.career_id].name if previous.career_id in catalog.careers else previous.career_id
        previous.status = "archived"
        db.flush()

    snap = build_snapshot(db, user, catalog)
    gap = analyze_gap(snap, career, catalog)
    projects = recommend_projects(snap, career, gap, catalog)
    plan = build_roadmap(snap, career, catalog, hours_per_week=profile.hours_per_week, flagship=projects["flagship"])

    rm = Roadmap(user_id=user.id, career_id=career.id, hours_per_week=plan["hours_per_week"],
                 version=(previous.version + 1) if previous else 1,
                 summary={"carried_over": carried, "switched_from": switched_from,
                          "covered": {ph["name"]: ph["covered"] for ph in plan["phases"]}})
    db.add(rm)
    db.flush()
    for ph in plan["phases"]:
        for order, st in enumerate(ph["steps"]):
            content = dict(st["content"])
            content.update({"importance": st["importance"], "optional": st["optional"], "is_prerequisite": st["is_prerequisite"]})
            db.add(RoadmapStep(roadmap_id=rm.id, phase_index=ph["index"], phase_name=ph["name"], order=order, kind=st["kind"],
                               skill_id=st["skill_id"], title=st["title"], est_hours=st["est_hours"],
                               from_level=st["from_level"], target_level=st["target_level"], content=content))
        if not ph["steps"]:
            # Keep covered phases visible so users see *why* they were skipped.
            db.add(RoadmapStep(roadmap_id=rm.id, phase_index=ph["index"], phase_name=ph["name"], order=0, kind="covered",
                               title=f"{ph['name']} — already covered", status="skipped", est_hours=0,
                               content={"covered": ph["covered"]}))
    db.commit()
    db.refresh(rm)
    return serialize_roadmap(rm, catalog)


def serialize_roadmap(rm: Roadmap, catalog: Catalog) -> dict:
    phases: dict[int, dict] = {}
    covered_map = (rm.summary or {}).get("covered", {})
    for s in rm.steps:
        ph = phases.setdefault(s.phase_index, {"index": s.phase_index, "name": s.phase_name, "steps": [],
                                               "covered": covered_map.get(s.phase_name, [])})
        if s.kind == "covered":
            continue
        c = s.content or {}
        ph["steps"].append({
            "id": s.id, "kind": s.kind, "skill_id": s.skill_id, "title": s.title, "status": s.status,
            "est_hours": s.est_hours, "from_level": s.from_level, "target_level": s.target_level,
            "importance": c.get("importance"), "optional": c.get("optional", False), "is_prerequisite": c.get("is_prerequisite", False),
            "content": c, "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        })
    ordered = [phases[k] for k in sorted(phases)]
    for ph in ordered:
        remaining = sum(st["est_hours"] for st in ph["steps"] if not st["optional"] and st["status"] not in ("done", "skipped"))
        total = sum(st["est_hours"] for st in ph["steps"] if not st["optional"])
        lo, hi, label = weeks_range(total, rm.hours_per_week)
        req = [st for st in ph["steps"] if not st["optional"]]
        done = [st for st in req if st["status"] in ("done", "skipped")]
        ph.update({
            "est_hours": total, "remaining_hours": remaining, "weeks_min": lo, "weeks_max": hi,
            "duration_label": label if ph["steps"] else "Already covered",
            "status": "covered" if not ph["steps"] else "done" if len(done) == len(req) else "in_progress" if done or any(st["status"] == "in_progress" for st in req) else "todo",
            "progress": round(len(done) / len(req), 3) if req else 1.0,
        })
    career = catalog.careers.get(rm.career_id)
    return {
        "id": rm.id,
        "career_id": rm.career_id,
        "career_name": career.name if career else rm.career_id,
        "version": rm.version,
        "generated_at": rm.generated_at.isoformat(),
        "hours_per_week": rm.hours_per_week,
        "phases": ordered,
        "carried_over": (rm.summary or {}).get("carried_over", []),
        "switched_from": (rm.summary or {}).get("switched_from"),
        "adjustments": (rm.summary or {}).get("adjustments", []),
        **summarize(ordered, rm.hours_per_week),
    }


def _get_step(db: Session, user: User, step_id: str) -> RoadmapStep:
    step = db.get(RoadmapStep, step_id)
    if not step or step.roadmap.user_id != user.id:
        raise NotFound("Roadmap step not found.")
    return step


def _raise_skill(db: Session, user: User, skill_id: str, level: int, source: str) -> None:
    row = db.scalars(select(UserSkill).where(UserSkill.user_id == user.id, UserSkill.skill_id == skill_id)).first()
    if row is None:
        db.add(UserSkill(user_id=user.id, skill_id=skill_id, level=level, source=source))
    elif row.level < level:
        row.level, row.source, row.unsure = level, source, False


def _log_adjustment(rm: Roadmap, text: str) -> None:
    summary = dict(rm.summary or {})
    summary["adjustments"] = ([{"at": datetime.now(timezone.utc).isoformat(), "text": text}] + summary.get("adjustments", []))[:10]
    rm.summary = summary


def update_step(db: Session, user: User, step_id: str, status: str, catalog: Catalog, *, evidence_url: str | None = None,
                note: str | None = None) -> dict:
    step = _get_step(db, user, step_id)
    step.status = status
    step.completed_at = datetime.now(timezone.utc) if status == "done" else None
    if status == "done":
        if step.kind == "skill" and step.skill_id:
            _raise_skill(db, user, step.skill_id, step.target_level, "roadmap")
            db.add(Progress(user_id=user.id, kind="skill", ref_id=step.id, skill_ids=[step.skill_id], title=step.title,
                            url=evidence_url, detail=note or "Completed roadmap step"))
        elif step.kind == "project":
            pid = (step.content or {}).get("project_id")
            tpl = catalog.projects.get(pid) if pid else None
            skills = tpl.skills if tpl else []
            db.add(Project(user_id=user.id, name=step.title.replace("Build: ", ""), description=(tpl.problem if tpl else ""),
                           technologies=tpl.technologies if tpl else [], status="completed", source="recommended",
                           template_id=pid, github_url=evidence_url,
                           analysis={"skill_ids": skills, "domains": tpl.domains if tpl else [], "difficulty": tpl.difficulty if tpl else "advanced"}))
            db.add(Progress(user_id=user.id, kind="project", ref_id=step.id, skill_ids=skills, title=step.title, url=evidence_url,
                            detail=note or "Portfolio project completed"))
        else:
            db.add(Progress(user_id=user.id, kind="artifact", ref_id=step.id, title=step.title, url=evidence_url, detail=note))
    db.commit()
    return serialize_roadmap(step.roadmap, catalog)


def mark_known(db: Session, user: User, skill_ids: list[str], catalog: Catalog) -> tuple[dict | None, list[str]]:
    """User says they already know these skills: record them and skip matching steps."""
    rm = active_roadmap(db, user)
    applied = []
    for sid in skill_ids:
        if sid not in catalog.skills:
            continue
        target = 2
        if rm:
            for step in rm.steps:
                if step.skill_id == sid and step.status not in ("done", "skipped"):
                    step.status = "skipped"
                    target = max(step.target_level, 1)
        _raise_skill(db, user, sid, target, "stated")
        applied.append(catalog.skill_name(sid))
    if rm and applied:
        _log_adjustment(rm, f"Skipped {', '.join(applied)} — you said you already know {'it' if len(applied) == 1 else 'them'}.")
    db.commit()
    return (serialize_roadmap(rm, catalog) if rm else None), applied


def set_hours(db: Session, user: User, hours: int, catalog: Catalog) -> dict | None:
    profile = get_or_create_profile(db, user)
    old = profile.hours_per_week
    profile.hours_per_week = hours
    rm = active_roadmap(db, user)
    if rm:
        rm.hours_per_week = hours
        _log_adjustment(rm, f"Re-timed your roadmap from {old} to {hours} hours per week.")
    db.commit()
    return serialize_roadmap(rm, catalog) if rm else None


def next_step(rm_data: dict) -> dict | None:
    for ph in rm_data["phases"]:
        for st in ph["steps"]:
            if st["status"] in ("todo", "in_progress") and not st["optional"]:
                return {**st, "phase_name": ph["name"]}
    return None
