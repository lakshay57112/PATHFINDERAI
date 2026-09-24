"""Job-market intelligence.

Two kinds of data:
  * user-ingested postings (pasted/uploaded job descriptions) — private to that user
  * a clearly labelled *synthetic* demo sample, generated from career templates so the
    feature is explorable offline. It is never presented as real market data.
Every analysis response names its data sources, sample size and time period.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import JobMarketData, User
from app.engines.extraction import aggregate_postings, extract_job_description
from app.knowledge.catalog import Catalog

SYNTHETIC_SOURCE = "PathFinder synthetic demo sample (generated — not real job postings)"
LOCATIONS = [
    ("India", "Bengaluru"), ("India", "Chandigarh"), ("India", "Hyderabad"), ("Germany", "Berlin"), ("Germany", "Munich"),
    ("United States", "New York"), ("United States", "San Francisco"), ("United Kingdom", "London"), ("Indonesia", "Jakarta"),
    ("Singapore", "Singapore"),
]
INDUSTRIES = ["Technology", "Finance", "Healthcare", "E-commerce", "Consulting", "Education"]
LEVEL_WORDS = {1: "familiarity with", 2: "solid experience with", 3: "deep expertise in"}


def _synthetic_posting(rng: random.Random, career, catalog: Catalog) -> dict:
    reqs = list(career.skills)
    must = [r for r in reqs if r.importance == "core" or rng.random() < 0.55]
    nice = [r for r in reqs if r not in must and rng.random() < 0.5]
    years = rng.choice([0, 1, 2, 2, 3, 3, 4, 5])
    country, city = rng.choice(LOCATIONS)
    industry = rng.choice(INDUSTRIES)
    remote = rng.random() < 0.3
    lines = [f"We're hiring a {career.name} to join our {industry.lower()} team.", "", "What you'll do:"]
    lines += [f"- {r}" for r in rng.sample(career.responsibilities, k=min(3, len(career.responsibilities)))]
    lines += ["", "What we're looking for:"]
    lines += [f"- {LEVEL_WORDS[r.level].capitalize()} {catalog.skill_name(r.skill_id)}" for r in must]
    if years:
        lines.append(f"- {years}+ years of relevant experience")
    lines.append(f"- {rng.choice(['Bachelor', 'Bachelor', 'Master']) }'s degree in a related field or equivalent practical experience")
    if career.certificates and rng.random() < 0.25:
        lines.append(f"- {catalog.certificates[rng.choice(career.certificates)].name} is a plus")
    if nice:
        lines += ["", "Nice to have: " + ", ".join(catalog.skill_name(r.skill_id) for r in nice)]
    techs = rng.sample(career.technologies, k=min(3, len(career.technologies)))
    lines += ["", "Our stack includes " + ", ".join(techs) + "."]
    return {"title": career.name, "description": "\n".join(lines), "country": "Remote" if remote else country,
            "city": None if remote else city, "remote": remote, "industry": industry,
            "posted_on": date(2026, 9, 20) - timedelta(days=rng.randint(0, 80))}


def seed_synthetic(db: Session, catalog: Catalog, per_career: int = 8) -> int:
    if db.scalar(select(func.count()).select_from(JobMarketData).where(JobMarketData.is_synthetic.is_(True))):
        return 0
    rng = random.Random(2026)
    n = 0
    for career in catalog.careers.values():
        for _ in range(per_career):
            p = _synthetic_posting(rng, career, catalog)
            db.add(JobMarketData(source=SYNTHETIC_SOURCE, is_synthetic=True, career_id=career.id,
                                 extracted=extract_job_description(p["title"], p["description"], catalog), **p))
            n += 1
    db.commit()
    return n


def ingest(db: Session, user: User | None, catalog: Catalog, *, source: str, career_id: str | None, postings: list[dict]) -> int:
    for p in postings:
        extracted = extract_job_description(p["title"], p["description"], catalog)
        cid = career_id or _guess_career(p["title"], extracted["skills"], catalog)
        db.add(JobMarketData(owner_id=user.id if user else None, source=source, is_synthetic=False, career_id=cid,
                             extracted=extracted, **p))
    db.commit()
    return len(postings)


def _guess_career(title: str, skills: list[str], catalog: Catalog) -> str | None:
    t = title.lower()
    for c in catalog.careers.values():
        if c.name.lower().split(" (")[0] in t:
            return c.id
    best = max(catalog.careers.values(), key=lambda c: len(set(skills) & {r.skill_id for r in c.skills}), default=None)
    return best.id if best else None


def _base_query(user: User):
    # Global data (owner NULL) plus the user's own private postings — never other users'.
    return select(JobMarketData).where(or_(JobMarketData.owner_id.is_(None), JobMarketData.owner_id == user.id))


def options(db: Session, user: User) -> dict:
    rows = db.execute(_base_query(user).with_only_columns(JobMarketData.country, JobMarketData.city, JobMarketData.industry)).all()
    return {"countries": sorted({r[0] for r in rows if r[0]}), "cities": sorted({r[1] for r in rows if r[1]}),
            "industries": sorted({r[2] for r in rows if r[2]})}


def analyze(db: Session, user: User, catalog: Catalog, *, career_id: str, country: str | None, city: str | None,
            remote: bool | None, industry: str | None, include_synthetic: bool, user_skills: dict[str, int]) -> dict:
    q = _base_query(user).where(JobMarketData.career_id == career_id)
    if country:
        q = q.where(JobMarketData.country == country)
    if city:
        q = q.where(JobMarketData.city == city)
    if remote is not None:
        q = q.where(JobMarketData.remote.is_(remote))
    if industry:
        q = q.where(JobMarketData.industry == industry)
    if not include_synthetic:
        q = q.where(JobMarketData.is_synthetic.is_(False))
    rows = db.scalars(q.limit(2000)).all()
    postings = [{"extracted": r.extracted} for r in rows]
    agg = aggregate_postings(postings, catalog, user_skills)
    sources: dict[str, dict] = {}
    for r in rows:
        s = sources.setdefault(r.source, {"source": r.source, "count": 0, "synthetic": r.is_synthetic, "yours": r.owner_id == user.id})
        s["count"] += 1
    dates = [r.posted_on for r in rows if r.posted_on]
    synthetic_only = bool(rows) and all(r.is_synthetic for r in rows)
    return {
        "career_id": career_id,
        "career_name": catalog.careers[career_id].name,
        "filters": {"country": country, "city": city, "remote": remote, "industry": industry},
        "sample_size": len(rows),
        "period": {"from": min(dates).isoformat(), "to": max(dates).isoformat()} if dates else None,
        "sources": list(sources.values()),
        "synthetic_only": synthetic_only,
        "headline": "Among the job descriptions analysed, these skills appear frequently." if rows else None,
        "insufficient": len(rows) < 5,
        **agg,
        "disclaimers": [
            "Frequency in job descriptions shows what employers ask for — it doesn't guarantee employment.",
            *(["This analysis uses a synthetic demo sample. Paste real job descriptions to analyse your actual market."] if synthetic_only else []),
        ],
    }
