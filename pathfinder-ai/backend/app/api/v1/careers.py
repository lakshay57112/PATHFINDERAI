from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai.pipeline import run_pipeline
from app.api.deps import catalog_dep, current_user, current_user_optional, rate_limit
from app.core.cache import get_cache
from app.core.errors import NotFound
from app.db.models import Recommendation, User
from app.db.session import get_db
from app.engines.matcher import compare, skill_coverage
from app.graphdb.store import get_graph
from app.knowledge.catalog import Catalog
from app.knowledge.vocab import ACTIVITIES, DOMAINS, EXPERIENCE_LEVELS, INTEREST_OPTIONS, LEARNING_PREFERENCES, LEVELS, WORK_STYLES
from app.schemas.api import CompareIn, DiscoverIn, SelectCareerIn
from app.services.profile_service import build_snapshot, get_or_create_profile

router = APIRouter(tags=["careers"])

EXPLORER_CATEGORIES = ["technology", "data", "ai", "business", "finance", "healthcare", "cybersecurity", "design", "marketing",
                       "science", "engineering", "product", "operations", "entrepreneurship", "cloud", "research", "education", "media"]


def _card(c) -> dict:
    return {"id": c.id, "name": c.name, "family": c.family, "categories": c.categories, "summary": c.summary,
            "skill_focus": c.skill_focus}


@router.get("/meta/vocab")
def vocab(catalog: Catalog = Depends(catalog_dep)):
    cached = get_cache().get_json("vocab:v1")
    if cached:
        return cached
    groups: dict[str, list] = {"languages": [], "ai_data": [], "tools": []}
    for s in catalog.skills.values():
        if s.onboarding in groups:
            groups[s.onboarding].append({"id": s.id, "name": s.name})
    out = {
        "interests": [{"id": d, "label": DOMAINS[d]} for d in INTEREST_OPTIONS],
        "activities": [{"id": k, "label": v["label"]} for k, v in ACTIVITIES.items()],
        "work_styles": [{"id": k, "label": v["label"]} for k, v in WORK_STYLES.items()],
        "skill_groups": groups,
        "all_skills": sorted(({"id": s.id, "name": s.name, "category": s.category} for s in catalog.skills.values()), key=lambda x: x["name"]),
        "levels": LEVELS,
        "experience_levels": EXPERIENCE_LEVELS,
        "learning_preferences": LEARNING_PREFERENCES,
    }
    get_cache().set_json("vocab:v1", out, ttl=3600)
    return out


@router.get("/careers")
def list_careers(category: str | None = None, q: str | None = Query(default=None, max_length=80), page: int = Query(1, ge=1),
                 page_size: int = Query(60, ge=1, le=100), catalog: Catalog = Depends(catalog_dep)):
    items = list(catalog.careers.values())
    if category:
        items = [c for c in items if category in c.categories]
    if q:
        ql = q.lower()
        items = [c for c in items if ql in c.name.lower() or ql in c.summary.lower()
                 or any(ql in catalog.skill_name(r.skill_id).lower() for r in c.skills)]
    items.sort(key=lambda c: c.name)
    start = (page - 1) * page_size
    return {"total": len(items), "page": page, "page_size": page_size, "items": [_card(c) for c in items[start:start + page_size]]}


@router.get("/careers/categories")
def categories(catalog: Catalog = Depends(catalog_dep)):
    by_cat = catalog.careers_by_category()
    return [{"id": c, "label": DOMAINS[c], "count": len(by_cat.get(c, [])),
             "careers": [x.name for x in sorted(by_cat.get(c, []), key=lambda x: x.name)][:6]}
            for c in EXPLORER_CATEGORIES if by_cat.get(c)]


@router.get("/careers/{career_id}")
def career_detail(career_id: str, user: User | None = Depends(current_user_optional), db: Session = Depends(get_db),
                  catalog: Catalog = Depends(catalog_dep)):
    c = catalog.careers.get(career_id)
    if not c:
        raise NotFound("Career not found.")
    snap = build_snapshot(db, user, catalog) if user else None
    skills = []
    for r in c.skills:
        s = catalog.skills[r.skill_id]
        row = {"skill_id": r.skill_id, "name": s.name, "category": s.category, "importance": r.importance,
               "target_level": r.level, "target_label": LEVELS[r.level]}
        if snap:
            row["your_level"] = snap.level(r.skill_id)
            row["your_label"] = LEVELS[snap.level(r.skill_id)]
        skills.append(row)
    phases = [{"name": p.name, "skills": [catalog.skill_name(s) for s in p.skills]} for p in c.phases]
    graph = get_graph()
    return {
        "id": c.id, "name": c.name, "family": c.family, "categories": c.categories, "summary": c.summary,
        "what_they_do": c.what_they_do, "responsibilities": c.responsibilities, "skills": skills,
        "technologies": c.technologies, "entry_routes": c.entry_routes, "example_projects": c.example_projects,
        "project_templates": [{"id": p, "name": catalog.projects[p].name, "difficulty": catalog.projects[p].difficulty} for p in c.project_templates],
        "certificates": [{"id": x, "name": catalog.certificates[x].name, "provider": catalog.certificates[x].provider} for x in c.certificates],
        "typical_learning_path": phases,
        "related": [{"id": r, "name": catalog.careers[r].name, "summary": catalog.careers[r].summary}
                    for r in graph.related_careers(c.id) if r in catalog.careers],
        "who_might_enjoy": c.who_might_enjoy, "questions_to_explore": c.questions_to_explore,
        "skill_focus": c.skill_focus, "typical_outputs": c.typical_outputs,
        "your_coverage": round(skill_coverage(snap, c), 2) if snap else None,
        "is_target": bool(user and user.profile and user.profile.target_career_id == c.id),
        "source_note": "Career information comes from PathFinder's curated knowledge base. Real roles vary by company and country.",
    }


@router.get("/graph/careers/{career_id}")
def career_graph(career_id: str, catalog: Catalog = Depends(catalog_dep)):
    if career_id not in catalog.careers:
        raise NotFound("Career not found.")
    g = get_graph()
    return {**g.career_subgraph(career_id), "backend": g.backend}


@router.get("/graph/skills/{skill_id}")
def skill_graph(skill_id: str, catalog: Catalog = Depends(catalog_dep)):
    if skill_id not in catalog.skills:
        raise NotFound("Skill not found.")
    g = get_graph()
    return {"skill_id": skill_id, "name": catalog.skill_name(skill_id), "related": g.related_skills(skill_id),
            "careers": [{"id": c, "name": catalog.careers[c].name} for c in g.careers_requiring(skill_id) if c in catalog.careers]}


@router.post("/career/discover", dependencies=[Depends(rate_limit("discover"))])
async def discover_careers(data: DiscoverIn | None = None, user: User = Depends(current_user), db: Session = Depends(get_db),
                           catalog: Catalog = Depends(catalog_dep)):
    snap = build_snapshot(db, user, catalog)
    state = await run_pipeline(snap, catalog, limit=(data.limit if data else 6))
    matches = state["matches"]
    db.query(Recommendation).filter(Recommendation.user_id == user.id, Recommendation.kind == "career").delete()
    for m in matches:
        db.add(Recommendation(user_id=user.id, kind="career", ref_id=m["career_id"], payload=m))
    db.commit()
    return {
        "intro": "Based on what you've told us, here are some paths worth exploring.",
        "matches": matches,
        "profile": state["profile"],
        "research": state["research"],
        "trace": state["trace"],
        "ai_enriched": state.get("ai_used", False),
        "principle": "These are possibilities to explore, not a verdict. You decide which direction fits.",
    }


@router.post("/career/compare")
def compare_careers(data: CompareIn, user: User | None = Depends(current_user_optional), db: Session = Depends(get_db),
                    catalog: Catalog = Depends(catalog_dep)):
    missing = [c for c in data.career_ids if c not in catalog.careers]
    if missing:
        raise NotFound(f"Unknown careers: {', '.join(missing)}")
    snap = build_snapshot(db, user, catalog) if user else None
    return compare(list(dict.fromkeys(data.career_ids)), catalog, snap)


@router.post("/career/select")
def select_career(data: SelectCareerIn, user: User = Depends(current_user), db: Session = Depends(get_db),
                  catalog: Catalog = Depends(catalog_dep)):
    if data.career_id not in catalog.careers:
        raise NotFound("Career not found.")
    profile = get_or_create_profile(db, user)
    profile.target_career_id = data.career_id
    db.commit()
    c = catalog.careers[data.career_id]
    return {"career_id": c.id, "name": c.name, "summary": c.summary,
            "message": "Now let's understand what it takes to get there."}
