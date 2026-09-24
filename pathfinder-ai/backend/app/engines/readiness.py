"""Evidence-based career readiness — deliberately *not* a single "job ready %" score."""
from __future__ import annotations

from collections import Counter

from app.engines.snapshot import ProfileSnapshot
from app.knowledge.catalog import Catalog
from app.knowledge.schema import CareerDef
from app.knowledge.vocab import a_an

AREA_PHRASES = {
    "infrastructure": "deployment and production engineering",
    "ai": "applied AI/ML",
    "data": "data work",
    "statistics": "statistics and quantitative reasoning",
    "programming": "programming",
    "software": "software engineering fundamentals",
    "security": "security practice",
    "business": "business and product skills",
    "finance": "finance knowledge",
    "marketing": "marketing skills",
    "design": "design practice",
    "healthcare": "healthcare domain skills",
    "research": "research practice",
    "professional": "communication and collaboration",
}

EVIDENCE_LABEL = {
    "assessment": "Assessed",
    "project": "Project evidence",
    "roadmap": "Completed roadmap step",
    "certificate": "Certificate",
    "stated": "Self-reported",
    "none": "No evidence yet",
}


def readiness(snapshot: ProfileSnapshot, career: CareerDef, catalog: Catalog) -> dict:
    buckets = {"strong": [], "developing": [], "limited": []}
    for req in career.skills:
        if req.importance == "useful":
            continue
        st = snapshot.state(req.skill_id)
        ratio = st.level / req.level
        strength = st.evidence_strength
        entry = {
            "skill_id": req.skill_id,
            "name": catalog.skill_name(req.skill_id),
            "importance": req.importance,
            "evidence": EVIDENCE_LABEL.get(strength, strength),
            "self_reported_only": strength == "stated",
        }
        if ratio >= 1:
            buckets["strong"].append(entry)
        elif ratio >= 0.5:
            buckets["developing"].append(entry)
        else:
            buckets["limited"].append(entry)

    weak = buckets["limited"] or buckets["developing"]
    # The weakest *area* is the category where the largest share of required skills lacks evidence.
    per_area = Counter(catalog.skills[r.skill_id].category for r in career.skills if r.importance != "useful")
    weak_area = Counter(catalog.skills[e["skill_id"]].category for e in weak)
    if weak_area:
        area = max(weak_area, key=lambda a: (weak_area[a] / per_area[a], weak_area[a],
                                             sum(e["importance"] == "core" for e in weak if catalog.skills[e["skill_id"]].category == a)))
        names = [e["name"] for e in weak if catalog.skills[e["skill_id"]].category == area][:3]
        next_step = f"Your strongest next step is to build evidence in {AREA_PHRASES.get(area, area)} ({', '.join(names)})."
    else:
        next_step = f"You cover the typical skill profile of {a_an(career.name)}. Focus on portfolio depth and interview practice."

    stated_only = [e["name"] for e in buckets["strong"] + buckets["developing"] if e["self_reported_only"]]
    return {
        "career_id": career.id,
        "career_name": career.name,
        "buckets": buckets,
        "next_step": next_step,
        "self_reported_note": (
            f"{', '.join(stated_only[:4])} {'is' if len(stated_only) == 1 else 'are'} currently self-reported. "
            "A project, assessment or certificate would make that evidence visible to others."
        ) if stated_only else None,
        "principle": "Readiness is shown as evidence, not a percentage. No tool can guarantee a job offer.",
    }
