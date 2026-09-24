"""Deterministic extraction from projects, certificates and job descriptions.

When an LLM is configured, ``app.ai`` can refine these results, but only through
validated schemas whose skill IDs must exist in the taxonomy.
"""
from __future__ import annotations

import re
from collections import Counter

from app.knowledge.catalog import Catalog
from app.knowledge.vocab import DOMAINS, LEVELS

DOMAIN_KEYWORDS = {
    "finance": ["finance", "financial", "fraud", "bank", "trading", "credit", "loan", "payment", "stock", "portfolio", "invest", "fintech"],
    "healthcare": ["health", "clinical", "patient", "medical", "hospital", "ehr", "disease", "genom"],
    "marketing": ["marketing", "campaign", "seo", "ads", "customer acquisition", "brand"],
    "education": ["education", "student", "course", "learning platform", "teach"],
    "ai": ["machine learning", "deep learning", "llm", "rag", "neural", "ai ", "model", "chatbot", "agent"],
    "data": ["data", "analytics", "dashboard", "sql", "etl"],
    "cybersecurity": ["security", "vulnerab", "threat", "malware", "pentest"],
    "design": ["ux", "ui ", "design", "prototype", "figma"],
    "business": ["business", "sales", "retail", "e-commerce", "ecommerce", "operations", "supply chain"],
    "cloud": ["aws", "azure", "gcp", "kubernetes", "cloud"],
    "research": ["research", "paper", "experiment", "study"],
}

ADVANCED_SIGNALS = ["deploy", "production", "kubernetes", "real-time", "scal", "distributed", "fine-tun", "monitor", "ci/cd", "users", "agent"]
LEVEL_WORDS = {3: ["professional", "advanced", "expert", "specialty"], 2: ["associate", "intermediate", "developer", "engineer"], 1: ["foundational", "fundamentals", "introduction", "intro", "beginner", "basics", "practitioner", "essentials"]}


def detect_domains(text: str) -> list[str]:
    t = f" {text.lower()} "
    hits = [(d, sum(t.count(k) for k in kws)) for d, kws in DOMAIN_KEYWORDS.items()]
    return [d for d, n in sorted(hits, key=lambda x: -x[1]) if n > 0][:3]


def analyze_project(name: str, description: str, technologies: list[str], catalog: Catalog) -> dict:
    text = " ".join([name or "", description or "", ", ".join(technologies or [])])
    skills = catalog.extract_skills(text)
    # Technologies listed explicitly are matched individually too (e.g. "XGBoost" -> machine_learning)
    for tech in technologies or []:
        for sid in catalog.extract_skills(tech):
            if sid not in skills:
                skills.append(sid)
    domains = detect_domains(text)
    low = text.lower()
    signal = sum(1 for s in ADVANCED_SIGNALS if s in low)
    adv_skills = sum(1 for s in skills if catalog.skills[s].category in ("infrastructure",) or s in ("ai_agents", "fine_tuning", "mlops"))
    points = len(skills) + 2 * signal + 2 * adv_skills
    difficulty = "advanced" if points >= 12 else "intermediate" if points >= 4 else "beginner"
    relevance = []
    sset = set(skills)
    for c in catalog.careers.values():
        core = {r.skill_id for r in c.skills if r.importance in ("core", "important")}
        overlap = sset & core
        if overlap:
            relevance.append((len(overlap) / len(core), c, overlap))
    relevance.sort(key=lambda t: -t[0])
    return {
        "skills_demonstrated": [{"skill_id": s, "name": catalog.skill_name(s)} for s in skills],
        "skill_ids": skills,
        "difficulty": difficulty,
        "domains": domains,
        "domain_labels": [DOMAINS[d] for d in domains],
        "technologies": technologies or [],
        "career_relevance": [
            {"career_id": c.id, "name": c.name, "matched_skills": [catalog.skill_name(s) for s in sorted(ov)]}
            for _, c, ov in relevance[:3]
        ],
        "method": "rules",
    }


def analyze_certificate(name: str, issuer: str | None, text: str, catalog: Catalog) -> dict:
    match = catalog.match_certificate(name, issuer)
    combined = " ".join(filter(None, [name, issuer, text]))
    skills = list(match.skills) if match else []
    for sid in catalog.extract_skills(combined):
        if sid not in skills:
            skills.append(sid)
    if match:
        level = match.level
    else:
        low = combined.lower()
        lvl = next((l for l, words in LEVEL_WORDS.items() if any(w in low for w in words)), 1)
        level = {1: "foundational", 2: "associate", 3: "professional"}[lvl]
    topics = sorted({catalog.skill_name(s) for s in skills})
    return {
        "certificate": match.name if match else name,
        "catalog_id": match.id if match else None,
        "provider": match.provider if match else (issuer or "Unknown"),
        "type": match.type if match else "unknown",
        "skills_covered": [{"skill_id": s, "name": catalog.skill_name(s)} for s in skills],
        "skill_ids": skills,
        "topics": topics,
        "level": level,
        "demonstrates": (
            f"{'A proctored exam' if match and match.type == 'exam' else 'Completed coursework'} covering {', '.join(topics[:4])}."
            if topics else "We couldn't identify specific skills yet — add a short description or upload the certificate."
        ),
        "matched_catalog": bool(match),
        "method": "rules",
    }


# ----------------------------------------------------------------- job descriptions
EDU_PATTERNS = {
    "Bachelor's degree": r"\b(bachelor'?s?|b\.?s\.?c?|b\.?tech|undergraduate degree)\b",
    "Master's degree": r"\b(master'?s?|m\.?s\.?c?|m\.?tech|mba)\b",
    "PhD": r"\b(ph\.?d|doctorate)\b",
}
EXP_RE = re.compile(r"(\d{1,2})\s*(?:\+|plus)?\s*(?:-|to|–)?\s*(?:\d{1,2})?\s*\+?\s*years?", re.I)
RESP_RE = re.compile(r"(?:^|\n)\s*(?:[-•*]\s*)?((?:build|design|develop|own|lead|work|collaborate|deploy|analy[sz]e|create|maintain|implement|partner|drive|manage|write|monitor)[^.\n]{15,160})", re.I)


def extract_job_description(title: str, description: str, catalog: Catalog) -> dict:
    text = f"{title}\n{description}"
    skills = catalog.extract_skills(text)
    years = [int(m.group(1)) for m in EXP_RE.finditer(text) if int(m.group(1)) <= 20]
    education = [label for label, pat in EDU_PATTERNS.items() if re.search(pat, text, re.I)]
    certs = []
    low = text.lower()
    for cert in catalog.certificates.values():
        base = re.split(r"\s[–-]\s", cert.name)[0]  # "AWS Certified X – Associate" is often written without the suffix
        for alias in [cert.name.lower(), base.lower(), *cert.aliases]:
            if len(alias) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(alias.lower())}(?![a-z0-9])", low):
                certs.append(cert.id)
                break
    responsibilities = [m.group(1).strip().rstrip(";,") for m in RESP_RE.finditer(description)][:6]
    return {
        "skills": skills,
        "min_years": min(years) if years else None,
        "education": education,
        "certifications": certs,
        "responsibilities": responsibilities,
    }


def aggregate_postings(postings: list[dict], catalog: Catalog, user_skills: dict[str, int] | None = None) -> dict:
    n = len(postings)
    if not n:
        return {"total": 0, "skills": [], "technologies": [], "experience": {}, "education": [], "certifications": [], "responsibilities": []}
    skill_counts, cert_counts, edu_counts = Counter(), Counter(), Counter()
    years: list[int] = []
    resp_counter = Counter()
    for p in postings:
        ex = p["extracted"]
        skill_counts.update(set(ex.get("skills", [])))
        cert_counts.update(set(ex.get("certifications", [])))
        edu_counts.update(set(ex.get("education", [])))
        if ex.get("min_years") is not None:
            years.append(ex["min_years"])
        for r in ex.get("responsibilities", [])[:3]:
            resp_counter[r[:1].upper() + r[1:]] += 1
    user_skills = user_skills or {}

    def row(sid, cnt):
        return {"skill_id": sid, "name": catalog.skill_name(sid), "category": catalog.skills[sid].category,
                "count": cnt, "share": round(cnt / n, 3), "you_have": user_skills.get(sid, 0) > 0,
                "your_level": LEVELS[user_skills.get(sid, 0)]}

    rows = [row(s, c) for s, c in skill_counts.most_common()]
    tech_cats = {"programming", "infrastructure", "data"}
    years_sorted = sorted(years)
    return {
        "total": n,
        "skills": [r for r in rows if r["category"] not in tech_cats][:15],
        "technologies": [r for r in rows if r["category"] in tech_cats][:15],
        "all_skills": rows[:30],
        "experience": {
            "postings_with_requirement": len(years),
            "median_min_years": years_sorted[len(years_sorted) // 2] if years_sorted else None,
            "distribution": dict(Counter(("0–1" if y <= 1 else "2–3" if y <= 3 else "4–6" if y <= 6 else "7+") for y in years)),
        },
        "education": [{"label": k, "count": v, "share": round(v / n, 3)} for k, v in edu_counts.most_common()],
        "certifications": [{"id": k, "name": catalog.certificates[k].name, "count": v, "share": round(v / n, 3)} for k, v in cert_counts.most_common(8)],
        "responsibilities": [r for r, _ in resp_counter.most_common(6)],
    }
