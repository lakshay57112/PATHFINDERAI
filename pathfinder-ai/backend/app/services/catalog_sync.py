"""Project the YAML knowledge base into relational catalog tables (idempotent)."""
from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Career, CareerResource, CareerSkill, CareerTechnology, Skill
from app.knowledge.catalog import Catalog

log = logging.getLogger("pathfinder.sync")


def sync_catalog(db: Session, catalog: Catalog) -> dict:
    existing_skills = {s.id: s for s in db.scalars(select(Skill))}
    for sd in catalog.skills.values():
        row = existing_skills.get(sd.id)
        if row is None:
            db.add(Skill(id=sd.id, name=sd.name, category=sd.category, description=sd.description))
        else:
            row.name, row.category, row.description = sd.name, sd.category, sd.description
    db.flush()

    changed = 0
    existing = {c.id: c for c in db.scalars(select(Career))}
    for cd in catalog.careers.values():
        h = catalog.career_hash(cd.id)
        row = existing.get(cd.id)
        if row is not None and row.content_hash == h:
            continue
        changed += 1
        if row is None:
            row = Career(id=cd.id)
            db.add(row)
        row.name, row.family, row.summary, row.data, row.content_hash = cd.name, cd.family, cd.summary, cd.model_dump(), h
        db.flush()
        db.execute(delete(CareerSkill).where(CareerSkill.career_id == cd.id))
        db.execute(delete(CareerTechnology).where(CareerTechnology.career_id == cd.id))
        db.execute(delete(CareerResource).where(CareerResource.career_id == cd.id))
        for req in cd.skills:
            db.add(CareerSkill(career_id=cd.id, skill_id=req.skill_id, target_level=req.level, importance=req.importance))
            for r in catalog.skills[req.skill_id].learn[:2]:
                db.add(CareerResource(career_id=cd.id, skill_id=req.skill_id, kind="learn", title=r.title, provider=r.provider, url=r.url))
        for t in cd.technologies:
            db.add(CareerTechnology(career_id=cd.id, name=t[:80]))
    db.commit()
    if changed:
        log.info("synced %d changed careers into the database", changed)
    return {"careers": len(catalog.careers), "skills": len(catalog.skills), "changed": changed}
