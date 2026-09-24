"""Reads and writes the user's profile; builds the engine snapshot."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.db.models import Certificate, Education, Interest, Profile, Progress, Project, User, UserSkill
from app.engines.extraction import analyze_certificate, analyze_project
from app.engines.snapshot import Evidence, ProfileSnapshot, SkillState, attach_evidence
from app.knowledge.catalog import Catalog
from app.knowledge.vocab import LEVEL_FROM_LABEL
from app.schemas.api import CertificateIn, OnboardingIn, ProjectIn, SkillIn


def get_or_create_profile(db: Session, user: User) -> Profile:
    if user.profile is None:
        user.profile = Profile(user_id=user.id)
        db.add(user.profile)
        db.flush()
    return user.profile


def build_snapshot(db: Session, user: User, catalog: Catalog) -> ProfileSnapshot:
    profile = get_or_create_profile(db, user)
    edu = user.education[0] if user.education else None
    snap = ProfileSnapshot(
        user_id=user.id,
        name=user.name,
        interests=[i.domain for i in user.interests],
        activities=list(profile.activities or []),
        work_styles=list(profile.work_styles or []),
        subjects=list(profile.subjects or []),
        education={"level": profile.education_level, "degree": profile.degree, "field": profile.field_of_study,
                   "institution": edu.institution if edu else None},
        experience_level=profile.experience_level,
        career_goals=profile.career_goals,
        learning_preferences=list(profile.learning_preferences or []),
        hours_per_week=profile.hours_per_week or 8,
        target_career_id=profile.target_career_id,
    )
    for us in user.skills:
        if us.skill_id not in catalog.skills:
            continue
        st = SkillState(us.skill_id, stated_level=us.level, unsure=us.unsure)
        if us.source in ("roadmap", "assessment"):
            st.evidence.append(Evidence(us.source, "Completed roadmap step" if us.source == "roadmap" else "Assessment"))
        snap.skills[us.skill_id] = st
    for c in user.certificates:
        snap.certificates.append({"id": c.id, "name": c.name, "catalog_id": c.catalog_id,
                                  "skills": (c.analysis or {}).get("skill_ids", [])})
    for p in user.projects:
        a = p.analysis or {}
        snap.projects.append({"id": p.id, "name": p.name, "skills": a.get("skill_ids", []), "domains": a.get("domains", []),
                              "status": p.status, "source": p.source, "template_id": p.template_id, "difficulty": a.get("difficulty")})
    # Assessment / quiz evidence recorded in the progress log
    for ev in db.scalars(select(Progress).where(Progress.user_id == user.id, Progress.kind.in_(("assessment", "quiz")))):
        for sid in ev.skill_ids or []:
            if sid in catalog.skills:
                snap.skills.setdefault(sid, SkillState(sid)).evidence.append(Evidence("assessment", ev.title, str(ev.id)))
    return attach_evidence(snap, catalog)


def _level(label: str) -> tuple[int, bool]:
    if label == "unsure":
        return 0, True
    return LEVEL_FROM_LABEL.get(label, 0), False


def set_skills(db: Session, user: User, skills: list[SkillIn], catalog: Catalog, *, replace: bool) -> None:
    unknown = [s.skill_id for s in skills if s.skill_id not in catalog.skills]
    if unknown:
        raise NotFound(f"Unknown skills: {', '.join(unknown)}")
    if replace:
        db.execute(delete(UserSkill).where(UserSkill.user_id == user.id, UserSkill.source == "stated"))
        db.flush()
        db.expire(user, ["skills"])
    current = {us.skill_id: us for us in user.skills}
    for s in skills:
        level, unsure = _level(s.level)
        row = current.get(s.skill_id)
        if row is None:
            row = UserSkill(user_id=user.id, skill_id=s.skill_id)
            db.add(row)
            current[s.skill_id] = row
        # Never downgrade evidence earned through the roadmap/assessments via a stated update.
        if row.source in ("roadmap", "assessment") and (row.level or 0) >= level:
            row.unsure = unsure and row.level == 0
            continue
        row.level, row.unsure, row.source = level, unsure, "stated"


def set_interests(db: Session, user: User, interests: list[str]) -> None:
    db.execute(delete(Interest).where(Interest.user_id == user.id))
    for d in interests:
        db.add(Interest(user_id=user.id, domain=d))
    db.flush()
    db.expire(user, ["interests"])


def add_certificate(db: Session, user: User, data: CertificateIn, catalog: Catalog, *, extracted_text: str = "",
                    file_key: str | None = None, file_mime: str | None = None) -> Certificate:
    analysis = analyze_certificate(data.name, data.issuer, " ".join(filter(None, [data.description, extracted_text])), catalog)
    cert = Certificate(user_id=user.id, name=data.name, issuer=data.issuer, completed_on=data.completed_on,
                       catalog_id=analysis["catalog_id"], analysis=analysis, file_key=file_key, file_mime=file_mime)
    db.add(cert)
    db.flush()
    db.add(Progress(user_id=user.id, kind="certificate", ref_id=cert.id, skill_ids=analysis["skill_ids"], title=data.name,
                    detail=analysis["demonstrates"]))
    return cert


def add_project(db: Session, user: User, data: ProjectIn, catalog: Catalog, *, source: str = "user", template_id: str | None = None) -> Project:
    analysis = analyze_project(data.name, data.description, data.technologies, catalog)
    proj = Project(user_id=user.id, name=data.name, description=data.description, technologies=data.technologies,
                   role=data.role, github_url=str(data.github_url) if data.github_url else None,
                   demo_url=str(data.demo_url) if data.demo_url else None, status=data.status, source=source,
                   template_id=template_id, analysis=analysis)
    db.add(proj)
    db.flush()
    if data.status == "completed":
        db.add(Progress(user_id=user.id, kind="project", ref_id=proj.id, skill_ids=analysis["skill_ids"], title=data.name,
                        url=proj.github_url or proj.demo_url, detail=f"{analysis['difficulty'].title()} project"))
    return proj


def save_onboarding(db: Session, user: User, data: OnboardingIn, catalog: Catalog) -> Profile:
    profile = get_or_create_profile(db, user)
    set_interests(db, user, data.interests)
    set_skills(db, user, data.skills, catalog, replace=True)
    profile.activities = data.activities
    profile.work_styles = data.work_styles
    profile.subjects = data.subjects
    if data.education:
        profile.education_level = data.education.level
        profile.degree = data.education.degree
        profile.field_of_study = data.education.field
        db.execute(delete(Education).where(Education.user_id == user.id))
        if any([data.education.degree, data.education.institution, data.education.field]):
            db.add(Education(user_id=user.id, institution=data.education.institution, degree=data.education.degree,
                             field_of_study=data.education.field))
    profile.experience_level = data.experience_level
    profile.work_experience = data.work_experience
    profile.internships = data.internships
    profile.career_goals = data.career_goals
    profile.learning_preferences = data.learning_preferences
    profile.hours_per_week = data.hours_per_week
    existing_certs = {c.name.lower() for c in user.certificates}
    for c in data.certificates:
        if c.name.lower() not in existing_certs:
            add_certificate(db, user, c, catalog)
    existing_projects = {p.name.lower() for p in user.projects}
    for p in data.projects:
        if p.name.lower() not in existing_projects:
            add_project(db, user, p, catalog)
    profile.onboarding_completed = True
    db.commit()
    db.refresh(user)
    return profile


def serialize_profile(user: User, catalog: Catalog) -> dict:
    p = user.profile
    return {
        "user": {"id": user.id, "email": user.email, "name": user.name, "is_demo": user.is_demo, "auth_provider": user.auth_provider},
        "onboarding_completed": bool(p and p.onboarding_completed),
        "interests": [i.domain for i in user.interests],
        "skills": [
            {"skill_id": s.skill_id, "name": catalog.skill_name(s.skill_id), "level": s.level, "unsure": s.unsure, "source": s.source}
            for s in sorted(user.skills, key=lambda s: (-s.level, s.skill_id))
        ],
        "activities": (p.activities if p else []) or [],
        "work_styles": (p.work_styles if p else []) or [],
        "subjects": (p.subjects if p else []) or [],
        "education": {"level": p.education_level, "degree": p.degree, "field": p.field_of_study} if p else {},
        "experience_level": p.experience_level if p else None,
        "work_experience": p.work_experience if p else None,
        "internships": p.internships if p else None,
        "career_goals": p.career_goals if p else None,
        "learning_preferences": (p.learning_preferences if p else []) or [],
        "hours_per_week": p.hours_per_week if p else 8,
        "target_career_id": p.target_career_id if p else None,
        "target_career_name": catalog.careers[p.target_career_id].name if p and p.target_career_id in catalog.careers else None,
        "certificates": [serialize_certificate(c) for c in user.certificates],
        "projects": [serialize_project(pr) for pr in user.projects],
    }


def serialize_certificate(c: Certificate) -> dict:
    return {"id": c.id, "name": c.name, "issuer": c.issuer, "completed_on": c.completed_on.isoformat() if c.completed_on else None,
            "catalog_id": c.catalog_id, "has_file": bool(c.file_key), "analysis": c.analysis or {}}


def serialize_project(p: Project) -> dict:
    return {"id": p.id, "name": p.name, "description": p.description, "technologies": p.technologies or [], "role": p.role,
            "github_url": p.github_url, "demo_url": p.demo_url, "status": p.status, "source": p.source,
            "template_id": p.template_id, "analysis": p.analysis or {}}
