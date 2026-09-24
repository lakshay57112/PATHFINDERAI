"""Certificate, project and learning-resource recommendation engines.

Every recommendation carries: recommendation, why, evidence, expected benefit, difficulty
and time required. Lists are deliberately short — a few well-explained options beat dozens.
"""
from __future__ import annotations

import math

from app.engines.snapshot import ProfileSnapshot
from app.knowledge.catalog import Catalog
from app.knowledge.schema import CareerDef, ProjectTemplate
from app.knowledge.vocab import DOMAINS, IMPORTANCE_WEIGHT, a_an

CERT_PREP_TIME = {
    "foundational": "Typically 2–6 weeks of part-time preparation",
    "intermediate": "Typically 1–3 months of part-time study",
    "associate": "Typically 1–3 months of part-time preparation",
    "professional": "Typically 3–6+ months; some require prior work experience",
}
CERT_DIFFICULTY = {"foundational": "Beginner", "intermediate": "Intermediate", "associate": "Intermediate", "professional": "Advanced"}


def _join(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


# --------------------------------------------------------------------- certificates
def recommend_certificates(snapshot: ProfileSnapshot, career: CareerDef, gap: dict, catalog: Catalog, *, limit: int = 3) -> dict:
    held = {c.get("catalog_id") for c in snapshot.certificates if c.get("catalog_id")}
    gap_ids = {i["skill_id"]: i for i in gap["items"] if i["status"] != "strong"}
    strong_ids = {i["skill_id"] for i in gap["items"] if i["status"] == "strong"}

    candidates = set(career.certificates)
    for cert in catalog.certificates.values():
        if len(set(cert.skills) & set(gap_ids)) >= 2:
            candidates.add(cert.id)

    scored = []
    for cid in candidates:
        cert = catalog.certificates[cid]
        if cid in held:
            continue
        covers = [s for s in cert.skills if s in gap_ids]
        overlap = [s for s in cert.skills if s in strong_ids]
        relevance = sum(IMPORTANCE_WEIGHT[gap_ids[s]["importance"]] for s in covers)
        if cid in career.certificates:
            relevance += 0.4
        if cert.type == "exam":
            relevance += 0.2  # proctored exams are stronger external validation than completion certificates
        relevance -= 0.35 * len(overlap)
        if cert.level == "professional" and snapshot.experience_level in (None, "student", "entry"):
            relevance -= 0.3
        scored.append((relevance, cert, covers, overlap))

    scored.sort(key=lambda t: -t[0])
    recs = []
    for relevance, cert, covers, overlap in scored:
        if relevance <= 0.3 or len(recs) >= limit:
            continue
        cover_names = [catalog.skill_name(s) for s in covers]
        overlap_names = [catalog.skill_name(s) for s in overlap]
        if cover_names and not overlap_names:
            verdict = "worth_exploring"
            why = f"This certificate could help cover {_join(cover_names)}, which are gaps for {a_an(career.name)}."
        elif cover_names:
            verdict = "consider"
            why = (f"This certificate could help cover {_join(cover_names)}, but your current profile already demonstrates "
                   f"{_join(overlap_names)}, so a project may provide stronger additional evidence.")
        else:
            verdict = "project_first"
            why = (f"Your profile already demonstrates {_join(overlap_names)}; a project would likely add more evidence than this certificate.")
        if cert.level == "professional" and snapshot.experience_level in (None, "student", "entry"):
            why += " It's a professional-level credential, so it may fit better later in your journey."
        recs.append({
            "id": cert.id,
            "name": cert.name,
            "provider": cert.provider,
            "type": cert.type,
            "level": cert.level,
            "url": cert.url,
            "verdict": verdict,
            "recommendation": cert.name,
            "why": why,
            "evidence": {"covers_gaps": cover_names, "already_demonstrated": overlap_names, "listed_for_career": cert.id in career.certificates},
            "expected_benefit": "External validation of " + (_join(cover_names) if cover_names else "skills you already have"),
            "difficulty": CERT_DIFFICULTY.get(cert.level, "Intermediate"),
            "time_required": CERT_PREP_TIME.get(cert.level, "Varies"),
            "notes": cert.notes,
        })

    existing = []
    for c in snapshot.certificates:
        cat = catalog.certificates.get(c.get("catalog_id") or "")
        skills = c.get("skills") or (cat.skills if cat else [])
        relevant = [catalog.skill_name(s) for s in skills if s in {r.skill_id for r in career.skills}]
        existing.append({
            "name": c.get("name"),
            "matched_catalog": cat.name if cat else None,
            "demonstrates": [catalog.skill_name(s) for s in skills if s in catalog.skills],
            "relevant_to_target": relevant,
        })

    return {
        "recommendations": recs,
        "existing": existing,
        "principle": "Practical evidence (projects, deployed work) usually says more than certificates alone. "
                     "Certificates are suggested only where they cover a real gap or add external validation.",
    }


# --------------------------------------------------------------------- projects
def _project_score(p: ProjectTemplate, snapshot: ProfileSnapshot, career: CareerDef, gap_ids: dict, strong_ids: set) -> tuple[float, list, list]:
    gaps_covered = [s for s in p.skills if s in gap_ids]
    strengths_used = [s for s in p.skills + p.uses if s in strong_ids]
    score = sum(IMPORTANCE_WEIGHT[gap_ids[s]["importance"]] for s in gaps_covered)
    score += 0.15 * len(strengths_used)
    if p.id in career.project_templates:
        score += 0.8
    if set(p.domains) & set(snapshot.interests):
        score += 0.3
    if any(pr.get("template_id") == p.id for pr in snapshot.projects):
        score -= 5  # already doing/done
    return score, gaps_covered, strengths_used


def personalise_project(p: ProjectTemplate, snapshot: ProfileSnapshot, catalog: Catalog, gaps_covered, strengths_used, career: CareerDef) -> dict:
    flavor_domain = next((d for d in snapshot.interests if d in p.flavors), None)
    name = p.name
    problem = p.problem
    if flavor_domain:
        name = f"{p.name} — {DOMAINS[flavor_domain]} edition"
        problem = f"{p.problem} Personalised angle: {p.flavors[flavor_domain]}"
    why_parts = []
    if gaps_covered:
        why_parts.append(f"builds evidence in {_join([catalog.skill_name(s) for s in gaps_covered[:3]])}")
    if strengths_used:
        why_parts.append(f"reuses your strengths in {_join([catalog.skill_name(s) for s in strengths_used[:3]])}")
    if flavor_domain:
        why_parts.append(f"connects to your interest in {DOMAINS[flavor_domain]}")
    why = ("It " + "; ".join(why_parts) + ".") if why_parts else f"It is a representative project for {a_an(career.name)}."
    hours = p.hours
    weeks = max(1, math.ceil(hours / max(snapshot.hours_per_week, 1)))
    return {
        "id": p.id,
        "name": name,
        "difficulty": p.difficulty,
        "problem": problem,
        "why_it_fits": why,
        "skills_learned": [catalog.skill_name(s) for s in p.skills],
        "skill_ids": p.skills,
        "technologies": p.technologies,
        "estimated_hours": hours,
        "estimated_time": f"~{hours:.0f} hours · about {weeks} week{'s' if weeks > 1 else ''} at {snapshot.hours_per_week} h/week",
        "architecture": p.architecture,
        "expected_output": p.expected_output,
        "portfolio_value": p.portfolio_value,
        "evidence": {"gaps_covered": [catalog.skill_name(s) for s in gaps_covered], "strengths_used": [catalog.skill_name(s) for s in strengths_used]},
        "domain_flavor": DOMAINS[flavor_domain] if flavor_domain else None,
    }


def recommend_projects(snapshot: ProfileSnapshot, career: CareerDef, gap: dict, catalog: Catalog) -> dict:
    gap_ids = {i["skill_id"]: i for i in gap["items"] if i["status"] != "strong"}
    strong_ids = {i["skill_id"] for i in gap["items"] if i["status"] in ("strong", "developing")} | set(snapshot.known_skill_ids(2))
    by_level: dict[str, list] = {"beginner": [], "intermediate": [], "advanced": []}
    career_skill_ids = {r.skill_id for r in career.skills}
    for p in catalog.projects.values():
        # Only projects that are genuinely about this career: curated for it, or ≥2 of its skills at their core.
        if p.id not in career.project_templates and len(set(p.skills) & career_skill_ids) < 2:
            continue
        score, gc, su = _project_score(p, snapshot, career, gap_ids, strong_ids)
        by_level[p.difficulty].append((score, p, gc, su))

    chosen: list[tuple] = []
    for level in ("beginner", "intermediate", "advanced"):
        opts = [o for o in sorted(by_level[level], key=lambda t: -t[0]) if o[2] and o[0] >= 0.6]
        if opts:
            chosen.append(opts[0])
    # Fill to three with the next most relevant projects when a rung has no good fit.
    rest = sorted((o for lvl in by_level.values() for o in lvl if o[2] and o[0] >= 0.6 and o not in chosen), key=lambda t: -t[0])
    while len(chosen) < 3 and rest:
        chosen.append(rest.pop(0))
    rank = {"beginner": 0, "intermediate": 1, "advanced": 2}
    chosen.sort(key=lambda t: (rank[t[1].difficulty], -t[0]))
    ladder = [personalise_project(p, snapshot, catalog, gc, su, career) for _, p, gc, su in chosen]

    # Suggest a starting rung based on current coverage of the career's core skills.
    core = [r for r in career.skills if r.importance == "core"]
    avg = sum(min(snapshot.level(r.skill_id) / r.level, 1) for r in core) / max(len(core), 1)
    start = "advanced" if avg >= 0.7 else "intermediate" if avg >= 0.35 else "beginner"
    available = [p["difficulty"] for p in ladder]
    if start not in available and available:
        start = available[-1] if start == "advanced" else available[0]
    for p in ladder:
        p["suggested_start"] = p["difficulty"] == start

    flagship = next((p for p in reversed(ladder)), None)
    return {"projects": ladder, "suggested_start": start, "flagship": flagship}


# --------------------------------------------------------------------- resources
def learning_plan_for_skill(skill_id: str, catalog: Catalog, *, from_level: int, to_level: int, career: CareerDef | None = None) -> dict:
    skill = catalog.skills[skill_id]
    focus = {
        (0, 1): "Fundamentals", (0, 2): "Fundamentals to working proficiency", (0, 3): "From zero to depth",
        (1, 2): "Beyond the basics", (1, 3): "Intermediate and advanced topics", (2, 3): "Advanced topics and depth",
    }.get((from_level, to_level), "Deepen your skills")
    project = None
    if career:
        project = next((catalog.projects[p] for p in career.project_templates if skill_id in catalog.projects[p].skills), None)
    return {
        "skill_id": skill_id,
        "name": skill.name,
        "focus": focus,
        "learn": [r.model_dump() for r in skill.learn],
        "practice": skill.practice,
        "build": (f"{skill.build} (or: {project.name})" if project else skill.build),
        "prove": skill.prove,
        "estimated_hours": skill.hours_between(from_level, to_level),
    }
