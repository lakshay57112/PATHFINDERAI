"""Profile Analyzer: turns stated interests, activities, skills and evidence into a career profile.

The domain bars are *affinity signals derived from what the user told us*, not psychometric
scores — the API response carries that disclaimer explicitly.
"""
from __future__ import annotations

import math
from collections import defaultdict

from app.engines.snapshot import ProfileSnapshot
from app.knowledge.catalog import Catalog
from app.knowledge.vocab import ACTIVITIES, DOMAINS, LEVELS, WORK_STYLES

DISCLAIMER = "Based on your stated interests and experience. These are signals to explore, not scientific measurements."

W_INTEREST = 3.0
W_ACTIVITY = 1.0
W_WORK_STYLE = 1.0
W_SKILL = 0.6
W_PROJECT = 0.5
SATURATION = 3.2


def domain_affinity(snapshot: ProfileSnapshot, catalog: Catalog) -> tuple[dict[str, float], dict[str, list[str]]]:
    """Return domain -> score (0..10) and domain -> human-readable reasons."""
    raw: dict[str, float] = defaultdict(float)
    reasons: dict[str, list[str]] = defaultdict(list)

    for d in snapshot.interests:
        if d in DOMAINS:
            raw[d] += W_INTEREST
            reasons[d].append("You selected it as an interest")
    for a in snapshot.activities:
        meta = ACTIVITIES.get(a)
        if not meta:
            continue
        for d, w in meta["domains"].items():
            raw[d] += W_ACTIVITY * w
            if w >= 0.6:
                reasons[d].append(f"You enjoy {meta['label'].lower()}")
    for ws in snapshot.work_styles:
        meta = WORK_STYLES.get(ws)
        if not meta:
            continue
        for d, w in meta["domains"].items():
            raw[d] += W_WORK_STYLE * w
            if w >= 0.6:
                reasons[d].append(f"“{meta['label']}” sounds interesting to you")
    for sid, st in snapshot.skills.items():
        skill = catalog.skills.get(sid)
        if not skill or st.level == 0:
            continue
        for i, d in enumerate(skill.domains):
            weight = W_SKILL * (st.level / 3) * (1.0 if i == 0 else 0.6)
            raw[d] += weight
            if i == 0 and st.level >= 2:
                reasons[d].append(f"{skill.name} ({LEVELS[st.level].lower()})")
    for proj in snapshot.projects:
        for d in proj.get("domains", []):
            if d in DOMAINS:
                raw[d] += W_PROJECT
                reasons[d].append(f"Project: {proj.get('name')}")

    scores = {d: round(10 * (1 - math.exp(-v / SATURATION)), 1) for d, v in raw.items() if v > 0}
    return scores, {d: _dedupe(r)[:4] for d, r in reasons.items()}


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def analyze_profile(snapshot: ProfileSnapshot, catalog: Catalog) -> dict:
    scores, reasons = domain_affinity(snapshot, catalog)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    domains = [
        {"domain": d, "label": DOMAINS[d], "score": s, "reasons": reasons.get(d, [])}
        for d, s in ranked
        if s >= 1.0
    ][:8]

    strengths = sorted(
        (st for st in snapshot.skills.values() if st.level >= 2 and st.skill_id in catalog.skills),
        key=lambda st: (-st.level, -len(st.evidence), catalog.skill_name(st.skill_id)),
    )
    developing = sorted(
        (st for st in snapshot.skills.values() if st.level == 1 and st.skill_id in catalog.skills),
        key=lambda st: catalog.skill_name(st.skill_id),
    )

    prefs = [ACTIVITIES[a]["label"] for a in snapshot.activities if a in ACTIVITIES]
    prefs += [WORK_STYLES[w]["label"] for w in snapshot.work_styles if w in WORK_STYLES]

    strong_interests = [DOMAINS[d] for d in snapshot.interests if d in DOMAINS]
    if not strong_interests:
        strong_interests = [d["label"] for d in domains[:3]]

    return {
        "name": snapshot.name,
        "disclaimer": DISCLAIMER,
        "domains": domains,
        "strong_interests": strong_interests[:5],
        "current_strengths": [
            {"skill_id": st.skill_id, "name": catalog.skill_name(st.skill_id), "level": st.level,
             "level_label": LEVELS[st.level], "evidence": [e.as_dict() for e in st.evidence]}
            for st in strengths[:8]
        ],
        "developing_skills": [
            {"skill_id": st.skill_id, "name": catalog.skill_name(st.skill_id), "level": st.level, "level_label": LEVELS[st.level]}
            for st in developing[:8]
        ],
        "unsure_skills": [catalog.skill_name(sid) for sid, st in snapshot.skills.items() if st.unsure and sid in catalog.skills],
        "work_preferences": prefs[:6],
        "summary": _summary(snapshot, strong_interests, strengths, prefs, catalog),
        "stats": {
            "skills": len([s for s in snapshot.skills.values() if s.level > 0]),
            "projects": len(snapshot.projects),
            "certificates": len(snapshot.certificates),
        },
    }


def _summary(snapshot, interests, strengths, prefs, catalog) -> str:
    parts = []
    if interests:
        parts.append(f"You're drawn to {_join(interests[:3])}")
    if strengths:
        parts.append(f"your strongest stated skills are {_join([catalog.skill_name(s.skill_id) for s in strengths[:3]])}")
    if prefs:
        parts.append(f"and you like {_join([p.lower() for p in prefs[:2]])}")
    if not parts:
        return "Tell us a little more about yourself to build a richer profile."
    text = ", ".join(parts[:-1]) + (" " if len(parts) > 1 else "") + parts[-1] if len(parts) > 1 else parts[0]
    return text[0].upper() + text[1:] + "."


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]
