"""Personalised roadmap generator.

The roadmap is built only from what the user still needs: skills already at the career's
target level are skipped, partially known skills start at the user's current level, and
missing prerequisites are inserted where they unlock later steps. Durations scale with
the user's available hours per week.
"""
from __future__ import annotations

import math

from app.engines.recommendations import learning_plan_for_skill
from app.engines.snapshot import ProfileSnapshot
from app.knowledge.catalog import Catalog
from app.knowledge.schema import CareerDef
from app.knowledge.vocab import IMPORTANCE_WEIGHT, LEVELS

PROFESSIONAL = {"communication", "stakeholder_management", "leadership"}
PORTFOLIO_EXTRA_STEPS = [
    {"title": "Deploy and document your flagship project", "hours": 6,
     "prove": "Live demo link, README with architecture diagram, evaluation or results section."},
    {"title": "Publish a case study and practise presenting it", "hours": 4,
     "prove": "A short write-up or video walkthrough; rehearse it in PathFinder's interview mode."},
]


def weeks_range(hours: float, hours_per_week: int) -> tuple[int, int, str]:
    if hours <= 0:
        return 0, 0, "Already covered"
    hpw = max(hours_per_week, 1)
    weeks = hours / hpw
    lo = max(1, math.floor(weeks * 0.8))
    hi = max(lo + 1, math.ceil(weeks * 1.25))
    return lo, hi, f"{lo}–{hi} weeks"


def _depths(skill_ids: list[str], catalog: Catalog) -> dict[str, int]:
    ids = set(skill_ids)
    memo: dict[str, int] = {}

    def depth(s: str, seen=()) -> int:
        if s in memo:
            return memo[s]
        pre = [p for p in catalog.skills[s].prereqs if p in ids and p not in seen]
        memo[s] = 0 if not pre else 1 + max(depth(p, seen + (s,)) for p in pre)
        return memo[s]

    return {s: depth(s) for s in skill_ids}


def _auto_phases(career: CareerDef, catalog: Catalog) -> list[dict]:
    ids = [r.skill_id for r in career.skills]
    depths = _depths(ids, catalog)
    buckets = {"Foundations": [], "Core Skills": [], "Specialisation": [], "Production & Deployment": [], "Professional Skills": []}
    for sid in ids:
        cat = catalog.skills[sid].category
        if sid in PROFESSIONAL:
            buckets["Professional Skills"].append(sid)
        elif cat == "infrastructure":
            buckets["Production & Deployment"].append(sid)
        elif depths[sid] == 0:
            buckets["Foundations"].append(sid)
        elif depths[sid] == 1:
            buckets["Core Skills"].append(sid)
        else:
            buckets["Specialisation"].append(sid)
    return [{"name": k, "skills": v} for k, v in buckets.items() if v]


def _topo(skill_ids: list[str], catalog: Catalog, priority: dict[str, float]) -> list[str]:
    ids = set(skill_ids)
    out: list[str] = []
    visiting: set[str] = set()

    def visit(s: str):
        if s in out or s in visiting:
            return
        visiting.add(s)
        for p in sorted((p for p in catalog.skills[s].prereqs if p in ids), key=lambda x: -priority.get(x, 0)):
            visit(p)
        visiting.discard(s)
        out.append(s)

    for s in sorted(skill_ids, key=lambda x: -priority.get(x, 0)):
        visit(s)
    return out


def build_roadmap(
    snapshot: ProfileSnapshot,
    career: CareerDef,
    catalog: Catalog,
    *,
    hours_per_week: int | None = None,
    flagship: dict | None = None,
) -> dict:
    hpw = hours_per_week or snapshot.hours_per_week or 8
    phases = [dict(name=p.name, skills=list(p.skills)) for p in career.phases] or _auto_phases(career, catalog)
    assigned = {s for p in phases for s in p["skills"]}
    for req in career.skills:  # place any requirement a curated phase list forgot
        if req.skill_id in assigned:
            continue
        target = next((p for p in phases if any(pre in p["skills"] for pre in catalog.skills[req.skill_id].prereqs)), None)
        target = target or next((p for p in phases if any(catalog.skills[s].category == catalog.skills[req.skill_id].category for s in p["skills"])), None)
        (target or phases[-1])["skills"].append(req.skill_id)
        assigned.add(req.skill_id)

    priority = {r.skill_id: IMPORTANCE_WEIGHT[r.importance] for r in career.skills}
    required = {r.skill_id for r in career.skills}
    added_prereqs: set[str] = set()
    out_phases = []

    for idx, ph in enumerate(phases):
        steps, covered = [], []
        phase_skills = list(ph["skills"])
        # Insert unmet prerequisites (outside the career's list) just before the skills they unlock.
        for sid in list(phase_skills):
            req = career.requirement(sid)
            if req and snapshot.level(sid) >= req.level:
                continue
            for pre in catalog.skills[sid].prereqs:
                if pre not in required and pre not in added_prereqs and snapshot.level(pre) == 0:
                    phase_skills.insert(phase_skills.index(sid), pre)
                    added_prereqs.add(pre)
                    priority[pre] = priority.get(sid, 0.5) + 0.01

        for sid in _topo(phase_skills, catalog, priority):
            req = career.requirement(sid)
            target = req.level if req else 1
            current = snapshot.level(sid)
            st = snapshot.state(sid)
            if current >= target:
                source = next((e.kind for e in st.evidence if e.kind == "roadmap"), None)
                covered.append({
                    "skill_id": sid, "name": catalog.skill_name(sid),
                    "reason": "Completed earlier in your journey" if source else f"You're already at {LEVELS[current].lower()} level",
                })
                continue
            plan = learning_plan_for_skill(sid, catalog, from_level=current, to_level=target, career=career)
            optional = bool(req and req.importance == "useful")
            steps.append({
                "kind": "skill",
                "skill_id": sid,
                "title": catalog.skill_name(sid) if current == 0 else f"{catalog.skill_name(sid)}: {LEVELS[current]} → {LEVELS[target]}",
                "from_level": current,
                "target_level": target,
                "importance": req.importance if req else "prerequisite",
                "optional": optional,
                "is_prerequisite": req is None,
                "est_hours": plan["estimated_hours"],
                "content": plan,
            })
        hours = sum(s["est_hours"] for s in steps if not s["optional"])
        lo, hi, label = weeks_range(hours, hpw)
        out_phases.append({
            "index": idx,
            "name": ph["name"],
            "status": "covered" if not steps else "todo",
            "steps": steps,
            "covered": covered,
            "est_hours": hours,
            "weeks_min": lo,
            "weeks_max": hi,
            "duration_label": label if steps else "Already covered",
        })

    # Final phase: portfolio evidence.
    if flagship:
        pf_steps = [{
            "kind": "project", "skill_id": None, "title": f"Build: {flagship['name']}",
            "from_level": 0, "target_level": 0, "importance": "core", "optional": False, "is_prerequisite": False,
            "est_hours": float(flagship.get("estimated_hours", 40)),
            "content": {"project_id": flagship["id"], "problem": flagship.get("problem"), "architecture": flagship.get("architecture"),
                        "expected_output": flagship.get("expected_output"), "why_it_fits": flagship.get("why_it_fits"),
                        "learn": [], "practice": "Break the build into weekly milestones.", "build": flagship.get("name"),
                        "prove": "Public repository, live demo and evaluation/results section."},
        }]
        for extra in PORTFOLIO_EXTRA_STEPS:
            pf_steps.append({
                "kind": "milestone", "skill_id": None, "title": extra["title"], "from_level": 0, "target_level": 0,
                "importance": "important", "optional": False, "is_prerequisite": False, "est_hours": float(extra["hours"]),
                "content": {"learn": [], "practice": "", "build": "", "prove": extra["prove"]},
            })
        hours = sum(s["est_hours"] for s in pf_steps)
        lo, hi, label = weeks_range(hours, hpw)
        out_phases.append({"index": len(out_phases), "name": "Portfolio", "status": "todo", "steps": pf_steps, "covered": [],
                           "est_hours": hours, "weeks_min": lo, "weeks_max": hi, "duration_label": label})

    return {
        "career_id": career.id,
        "career_name": career.name,
        "hours_per_week": hpw,
        "phases": out_phases,
        **summarize(out_phases, hpw),
    }


def summarize(phases: list[dict], hours_per_week: int) -> dict:
    """Recompute totals from step statuses (used after every adaptive change)."""
    total = remaining = 0.0
    skills_total = skills_done = 0
    for ph in phases:
        for s in ph["steps"]:
            if s.get("optional"):
                continue
            total += s["est_hours"]
            if s.get("status", "todo") not in ("done", "skipped"):
                remaining += s["est_hours"]
            if s["kind"] == "skill":
                skills_total += 1
                skills_done += s.get("status") in ("done", "skipped")
    lo, hi, label = weeks_range(remaining, hours_per_week)
    return {
        "total_hours": round(total, 1),
        "remaining_hours": round(remaining, 1),
        "remaining_weeks_min": lo,
        "remaining_weeks_max": hi,
        "remaining_label": label if remaining else "Complete",
        "skills_total": skills_total,
        "skills_done": skills_done,
        "timeline_note": f"Estimated at {hours_per_week} hours per week. Estimates are rough guides — go at the pace that works for you.",
    }
