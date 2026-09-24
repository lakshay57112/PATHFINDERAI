"""Idempotent seeding: catalog projection, demo user, synthetic market sample."""
from __future__ import annotations

import logging

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import User
from app.knowledge.catalog import Catalog
from app.schemas.api import CertificateIn, EducationIn, OnboardingIn, ProjectIn, SkillIn
from app.services import market_service
from app.services import roadmap_service as rs
from app.services.catalog_sync import sync_catalog
from app.services.profile_service import save_onboarding

log = logging.getLogger("pathfinder.seed")


def demo_onboarding() -> tuple[dict, OnboardingIn]:
    d = yaml.safe_load((get_settings().data_dir / "demo_user.yaml").read_text(encoding="utf-8"))
    skills = [SkillIn(skill_id=k, level=v) for k, v in d["skills"].items()] + [SkillIn(skill_id=k, level="unsure") for k in d.get("unsure", [])]
    payload = OnboardingIn(
        interests=d["interests"], skills=skills, activities=d["activities"], work_styles=d["work_styles"],
        subjects=d.get("subjects", []), education=EducationIn(**d["education"]), experience_level=d["experience_level"],
        internships=d.get("internships"), career_goals=d.get("career_goals"), learning_preferences=d.get("learning_preferences", []),
        hours_per_week=d["hours_per_week"], certificates=[CertificateIn(**c) for c in d["certificates"]],
        projects=[ProjectIn(**p) for p in d["projects"]],
    )
    return d, payload


def reset_demo_user(db: Session, catalog: Catalog, *, with_roadmap: bool = True) -> User:
    d, payload = demo_onboarding()
    user = db.scalar(select(User).where(User.email == d["email"]))
    if user:
        db.delete(user)
        db.commit()
    user = User(email=d["email"], name=d["name"], password_hash=hash_password(d["password"]), is_demo=True)
    db.add(user)
    db.commit()
    save_onboarding(db, user, payload, catalog)
    if with_roadmap:
        rs.generate_roadmap(db, user, catalog, career_id="ai-engineer")
        rm = rs.active_roadmap(db, user)
        first = next((s for s in rm.steps if s.kind == "skill"), None)
        if first:
            rs.update_step(db, user, first.id, "done", catalog, note="Built a FastAPI service for the RAG chatbot")
    return user


def seed_all(db: Session, catalog: Catalog) -> dict:
    out = {"catalog": sync_catalog(db, catalog)}
    if get_settings().seed_demo_user and not db.scalar(select(User).where(User.is_demo.is_(True))):
        reset_demo_user(db, catalog)
        out["demo_user"] = "created"
    out["market_postings"] = market_service.seed_synthetic(db, catalog)
    return out
