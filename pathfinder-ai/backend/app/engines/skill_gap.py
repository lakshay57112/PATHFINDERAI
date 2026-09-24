"""Skill Gap engine: compares the user's current profile with a target career."""
from __future__ import annotations

from app.engines.snapshot import ProfileSnapshot
from app.knowledge.catalog import Catalog
from app.knowledge.schema import CareerDef
from app.knowledge.vocab import IMPORTANCE_WEIGHT, LEVELS, a_an

STATUS_LABELS = {
    "strong": "Strong",
    "developing": "Developing",
    "needs_development": "Needs development",
    "not_explored": "Not yet explored",
}


def status_for(current: int, target: int) -> str:
    if current <= 0:
        return "not_explored"
    ratio = current / target
    if ratio >= 1:
        return "strong"
    if ratio >= 0.6:
        return "developing"
    return "needs_development"


def _dependents(career: CareerDef, catalog: Catalog) -> dict[str, int]:
    """How many other required skills list each skill as a prerequisite (unlocks more learning)."""
    ids = {r.skill_id for r in career.skills}
    counts: dict[str, int] = {}
    for r in career.skills:
        for p in catalog.skills[r.skill_id].prereqs:
            if p in ids:
                counts[p] = counts.get(p, 0) + 1
    return counts


def analyze_gap(snapshot: ProfileSnapshot, career: CareerDef, catalog: Catalog) -> dict:
    deps = _dependents(career, catalog)
    items = []
    for req in career.skills:
        skill = catalog.skills[req.skill_id]
        st = snapshot.state(req.skill_id)
        current = st.level
        status = status_for(current, req.level)
        gap = max(req.level - current, 0)
        priority = IMPORTANCE_WEIGHT[req.importance] * (gap / req.level) + 0.08 * deps.get(req.skill_id, 0)
        items.append({
            "skill_id": req.skill_id,
            "name": skill.name,
            "category": skill.category,
            "importance": req.importance,
            "target_level": req.level,
            "target_label": LEVELS[req.level],
            "current_level": current,
            "current_label": LEVELS[current],
            "unsure": st.unsure,
            "status": status,
            "status_label": STATUS_LABELS[status],
            "bar": round(min(current / req.level, 1.0) * 10),
            "priority": round(priority, 3),
            "evidence": [e.as_dict() for e in st.evidence] or ([{"kind": "stated", "title": f"You said: {LEVELS[st.stated_level].lower()}", "ref_id": None}] if st.stated_level else []),
            "explanation": _explain(req, skill, career, catalog, current) if status != "strong" else None,
        })

    order = {"core": 0, "important": 1, "useful": 2}
    items.sort(key=lambda i: (i["status"] == "strong", -i["priority"], order[i["importance"]]))
    strengths = [i for i in items if i["status"] == "strong"]
    gaps = [i for i in items if i["status"] != "strong"]
    priority_gaps = [g for g in gaps if g["importance"] != "useful"][:6] or gaps[:6]
    return {
        "career_id": career.id,
        "career_name": career.name,
        "items": items,
        "strengths": [i["name"] for i in sorted(strengths, key=lambda i: order[i["importance"]])],
        "priority_gaps": [g["name"] for g in priority_gaps],
        "priority_gap_ids": [g["skill_id"] for g in priority_gaps],
        "counts": {
            "strong": len(strengths),
            "developing": len([g for g in gaps if g["status"] == "developing"]),
            "needs_development": len([g for g in gaps if g["status"] == "needs_development"]),
            "not_explored": len([g for g in gaps if g["status"] == "not_explored"]),
        },
        "note": "Your side comes from what you told us plus evidence from your projects and certificates. "
                "The career side comes from PathFinder's career knowledge base.",
    }


def _explain(req, skill, career: CareerDef, catalog: Catalog, current: int) -> dict:
    project = next(
        (catalog.projects[p] for p in career.project_templates if req.skill_id in catalog.projects[p].skills), None
    ) or next((p for p in catalog.projects.values() if req.skill_id in p.skills), None)
    cert = next(
        (catalog.certificates[c] for c in career.certificates if req.skill_id in catalog.certificates[c].skills), None
    )
    imp = {"core": "a core skill", "important": "an important skill", "useful": "a useful supporting skill"}[req.importance]
    focus = f"Move from {LEVELS[current].lower()} to {LEVELS[req.level].lower()}" if current else f"Build {a_an(LEVELS[req.level].lower() + '-level')} foundation"
    return {
        "why_it_matters": f"{skill.description} For {a_an(career.name)}, it's {imp}.",
        "what_to_learn": focus + ".",
        "resources": [r.model_dump() for r in skill.learn[:2]],
        "suggested_practice": skill.practice,
        "suggested_project": {"id": project.id, "name": project.name} if project else None,
        "optional_certificate": {"id": cert.id, "name": cert.name, "provider": cert.provider} if cert else None,
    }
