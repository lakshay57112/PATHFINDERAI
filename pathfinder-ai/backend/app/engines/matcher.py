"""Career Discovery engine.

Scores each career on three transparent signals and explains every recommendation:
  interest fit  – overlap between the user's domain affinity and the career's domains
  activity fit  – overlap between what the user enjoys / wants to do and the career's work
  skill fit     – how much of the career's skill profile the user already covers
The overall score is only used for ordering; the UI shows the reasons, not a number.
"""
from __future__ import annotations

from app.engines.profile_analyzer import domain_affinity
from app.engines.snapshot import ProfileSnapshot
from app.knowledge.catalog import Catalog
from app.knowledge.schema import CareerDef
from app.knowledge.vocab import ACTIVITIES, COMPARISON_DIMENSIONS, DOMAINS, EMPHASIS_LABELS, IMPORTANCE_WEIGHT, LEVELS, WORK_STYLES

W_INTEREST, W_ACTIVITY, W_SKILL = 0.45, 0.20, 0.35


def skill_coverage(snapshot: ProfileSnapshot, career: CareerDef) -> float:
    total = sum(IMPORTANCE_WEIGHT[r.importance] for r in career.skills)
    if not total:
        return 0.0
    got = sum(IMPORTANCE_WEIGHT[r.importance] * min(snapshot.level(r.skill_id) / r.level, 1.0) for r in career.skills)
    return got / total


def score_career(snapshot: ProfileSnapshot, career: CareerDef, affinity: dict[str, float]) -> dict:
    weights = career.signals.domains or {c: 1.0 for c in career.categories}
    wsum = sum(weights.values()) or 1.0
    interest_fit = sum(w * affinity.get(d, 0) / 10 for d, w in weights.items()) / wsum
    # Emphasise the career's primary domain so broad profiles don't flatten everything.
    primary = max(weights, key=weights.get)
    interest_fit = 0.6 * interest_fit + 0.4 * affinity.get(primary, 0) / 10
    # Explicitly chosen interests are the strongest signal we have — reward careers that touch them.
    explicit = set(snapshot.interests)
    if explicit:
        interest_fit = 0.7 * interest_fit + 0.3 * (sum(w for d, w in weights.items() if d in explicit) / wsum)

    acts = set(career.signals.activities)
    styles = set(career.signals.work_styles)
    act_hits = acts & set(snapshot.activities)
    style_hits = styles & set(snapshot.work_styles)
    # Jaccard overlap, so careers with very short activity lists don't get inflated scores.
    act_union = acts | set(snapshot.activities)
    style_union = styles | set(snapshot.work_styles)
    activity_fit = 0.5 * (len(act_hits) / len(act_union) if act_union else 0) + 0.5 * (len(style_hits) / len(style_union) if style_union else 0)

    skill_fit = skill_coverage(snapshot, career)
    score = W_INTEREST * interest_fit + W_ACTIVITY * activity_fit + W_SKILL * skill_fit
    return {
        "score": round(score, 4),
        "interest_fit": round(interest_fit, 3),
        "activity_fit": round(activity_fit, 3),
        "skill_fit": round(skill_fit, 3),
        "activity_hits": sorted(act_hits),
        "style_hits": sorted(style_hits),
    }


def explain(snapshot: ProfileSnapshot, career: CareerDef, parts: dict, catalog: Catalog) -> dict:
    reasons: list[dict] = []
    tokens: list[str] = []

    # Matched skills — core first, strongest first.
    matched = [
        r for r in career.skills if snapshot.level(r.skill_id) > 0
    ]
    matched.sort(key=lambda r: (-IMPORTANCE_WEIGHT[r.importance], -snapshot.level(r.skill_id)))
    for r in matched[:4]:
        st = snapshot.state(r.skill_id)
        name = catalog.skill_name(r.skill_id)
        detail = f"You: {LEVELS[st.level].lower()}"
        ev = [e.title for e in st.evidence if e.kind in ("project", "certificate")]
        if ev:
            detail += f" · shown in {ev[0]}"
        reasons.append({"type": "skill", "label": name, "detail": detail, "source": "your_profile"})
        tokens.append(name)

    interest_hits = [d for d in snapshot.interests if d in (career.signals.domains or {}) or d in career.categories]
    for d in interest_hits[:3]:
        reasons.append({"type": "interest", "label": DOMAINS[d], "detail": "You selected this interest", "source": "your_profile"})
        tokens.append(DOMAINS[d])
    for a in parts["activity_hits"][:2]:
        label = ACTIVITIES[a]["label"]
        reasons.append({"type": "activity", "label": label, "detail": "You said you enjoy this", "source": "your_profile"})
        tokens.append(label.lower())
    for w in parts["style_hits"][:2]:
        label = WORK_STYLES[w]["label"]
        reasons.append({"type": "work_style", "label": label, "detail": "You said this kind of work sounds interesting", "source": "your_profile"})

    project_hits = [
        p["name"] for p in snapshot.projects
        if set(p.get("skills", [])) & {r.skill_id for r in career.skills if r.importance == "core"}
    ]
    for pname in project_hits[:2]:
        reasons.append({"type": "project", "label": pname, "detail": "Uses core skills of this career", "source": "your_profile"})

    gaps = sorted(
        (r for r in career.skills if r.importance == "core" and snapshot.level(r.skill_id) < r.level),
        key=lambda r: snapshot.level(r.skill_id) / r.level,
    )
    to_explore = [catalog.skill_name(r.skill_id) for r in gaps[:3]]

    return {"reasons": reasons, "why_summary": " + ".join(dict.fromkeys(tokens[:5])), "to_explore": to_explore}


def _primary(career: CareerDef) -> str:
    doms = career.signals.domains or {c: 1.0 for c in career.categories}
    return max(doms, key=doms.get)


def fit_label(score: float) -> str:
    if score >= 0.6:
        return "Strong overlap"
    if score >= 0.45:
        return "Clear overlap"
    if score >= 0.3:
        return "Some overlap"
    return "Worth a look"


def discover(snapshot: ProfileSnapshot, catalog: Catalog, *, limit: int = 6, min_score: float = 0.2) -> list[dict]:
    affinity, _ = domain_affinity(snapshot, catalog)
    scored = []
    for career in catalog.careers.values():
        parts = score_career(snapshot, career, affinity)
        scored.append((career, parts))
    scored.sort(key=lambda cp: -cp[1]["score"])

    # Diversity re-ranking (MMR-style): gently penalise paths whose primary domain is already
    # represented, so the user sees several genuinely different directions.
    picked: list[tuple[CareerDef, dict]] = []
    pool = scored[: max(limit * 4, 20)]
    while pool and len(picked) < limit:
        def adjusted(cp):
            prim = _primary(cp[0])
            same = sum(1 for c, _ in picked if _primary(c) == prim)
            return cp[1]["score"] - 0.05 * same
        best = max(pool, key=adjusted)
        pool.remove(best)
        picked.append(best)

    results = []
    for career, parts in picked:
        if parts["score"] < min_score and results:
            break
        exp = explain(snapshot, career, parts, catalog)
        results.append({
            "career_id": career.id,
            "name": career.name,
            "family": career.family,
            "summary": career.summary,
            "fit_label": fit_label(parts["score"]),
            "signals": {k: parts[k] for k in ("interest_fit", "activity_fit", "skill_fit")},
            "score": parts["score"],
            **exp,
        })
        if len(results) >= limit:
            break
    return results


# ------------------------------------------------------------------ comparison
def emphasis(career: CareerDef, catalog: Catalog, categories: list[str]) -> int:
    """0–3 emphasis of a dimension, derived from how many and how deep the career's skills go there."""
    reqs = [r for r in career.skills if catalog.skills[r.skill_id].category in categories]
    if not reqs:
        return 0
    weight = sum(IMPORTANCE_WEIGHT[r.importance] * r.level for r in reqs)
    if weight >= 7:
        return 3
    if weight >= 3.5:
        return 2
    return 1


def compare(career_ids: list[str], catalog: Catalog, snapshot: ProfileSnapshot | None = None) -> dict:
    careers = [catalog.careers[c] for c in career_ids]
    columns = []
    for c in careers:
        dims = {}
        for key, meta in COMPARISON_DIMENSIONS.items():
            e = emphasis(c, catalog, meta["categories"])
            dims[key] = {"level": e, "label": EMPHASIS_LABELS[e]}
        core = [catalog.skill_name(r.skill_id) for r in c.skills if r.importance == "core"]
        col = {
            "career_id": c.id,
            "name": c.name,
            "skill_focus": c.skill_focus,
            "dimensions": dims,
            "typical_outputs": c.typical_outputs,
            "learning_areas": core[:6],
            "technologies": c.technologies[:6],
        }
        if snapshot is not None:
            col["your_coverage"] = round(skill_coverage(snapshot, c), 2)
            col["you_already_have"] = [
                catalog.skill_name(r.skill_id) for r in c.skills if snapshot.level(r.skill_id) >= r.level
            ][:6]
        columns.append(col)
    shared = set.intersection(*[{r.skill_id for r in c.skills} for c in careers]) if careers else set()
    return {
        "careers": columns,
        "rows": [{"key": k, "label": v["label"]} for k, v in COMPARISON_DIMENSIONS.items()],
        "shared_skills": sorted(catalog.skill_name(s) for s in shared),
        "note": "Emphasis levels are derived from each career's typical skill profile in our knowledge base. Real roles vary by company.",
    }
