"""AI evaluation suite.

Measures recommendation relevance, explanation quality, hallucination rate, citation correctness and
career-resource relevance against a small set of labelled personas. These run offline against the
deterministic engines; set LLM_PROVIDER to run the same checks over AI-enriched output.
"""
import asyncio

import pytest

from app.ai.guards import FORBIDDEN_CLAIMS
from app.ai.pipeline import run_pipeline
from app.engines.matcher import discover
from app.engines.recommendations import recommend_projects
from app.engines.roadmap import build_roadmap
from app.engines.skill_gap import analyze_gap
from app.rag.retriever import get_retriever
from tests.conftest import make_snapshot

PERSONAS = [
    {"name": "ai_builder", "interests": ["ai", "technology"], "skills": {"python": "advanced", "machine_learning": "intermediate", "llms": "beginner"},
     "activities": ["building", "technology"], "work_styles": ["build_software", "research_technology"],
     "expected": {"ai-engineer", "ml-engineer", "genai-engineer"}},
    {"name": "finance_analyst", "interests": ["finance", "data"], "skills": {"excel": "advanced", "sql": "intermediate", "accounting": "intermediate"},
     "activities": ["numbers", "analyzing_data"], "work_styles": ["financial_information", "analyze_information"],
     "expected": {"financial-analyst", "financial-data-analyst", "investment-analyst", "risk-analyst"}},
    {"name": "security_curious", "interests": ["cybersecurity", "technology"], "skills": {"linux": "intermediate", "networking": "beginner"},
     "activities": ["problem_solving", "technology"], "work_styles": ["research_technology"],
     "expected": {"cybersecurity-engineer", "security-analyst", "penetration-tester"}},
    {"name": "designer", "interests": ["design"], "skills": {"ui_design": "intermediate"}, "activities": ["designing", "people"],
     "work_styles": ["design_experiences"], "expected": {"ux-designer", "ui-designer", "product-designer", "ux-researcher"}},
    {"name": "health_data", "interests": ["healthcare", "data"], "skills": {"sql": "intermediate", "statistics": "beginner"},
     "activities": ["analyzing_data"], "work_styles": ["work_with_data"],
     "expected": {"health-data-analyst", "health-informatics-specialist", "healthcare-ai-engineer"}},
    {"name": "founder", "interests": ["entrepreneurship", "business"], "skills": {"communication": "intermediate"},
     "activities": ["starting_businesses", "people"], "work_styles": ["create_products", "manage_teams"],
     "expected": {"entrepreneur", "product-manager", "technical-founder"}},
    {"name": "marketer", "interests": ["marketing", "data"], "skills": {"digital_marketing": "intermediate", "excel": "intermediate"},
     "activities": ["analyzing_data", "writing"], "work_styles": ["work_with_customers", "analyze_information"],
     "expected": {"digital-marketing-analyst", "marketing-analyst", "growth-analyst", "seo-specialist"}},
]


def _snap(catalog, p):
    return make_snapshot(catalog, interests=p["interests"], skills=p["skills"], activities=p["activities"], work_styles=p["work_styles"])


def test_recommendation_relevance(catalog):
    """Hit@3: at least one labelled-relevant career in the top 3 for every persona; report precision@5."""
    hits, precision = 0, []
    for p in PERSONAS:
        top = [m["career_id"] for m in discover(_snap(catalog, p), catalog, limit=5)]
        hits += bool(set(top[:3]) & p["expected"])
        precision.append(len(set(top) & p["expected"]) / 5)
    hit_rate = hits / len(PERSONAS)
    print(f"\nHit@3={hit_rate:.2f}  mean Precision@5={sum(precision) / len(precision):.2f}")
    assert hit_rate == 1.0
    assert sum(precision) / len(precision) >= 0.35


@pytest.mark.parametrize("p", PERSONAS, ids=[p["name"] for p in PERSONAS])
def test_explanation_quality(catalog, p):
    """Every reason must be traceable to something the user actually provided."""
    snap = _snap(catalog, p)
    provided = {catalog.skill_name(s) for s in snap.skills} | {x for x in snap.interests}
    for m in discover(snap, catalog, limit=5):
        assert len(m["reasons"]) >= 2, m["name"]
        for r in m["reasons"]:
            if r["type"] == "skill":
                assert r["label"] in provided
            if r["type"] == "interest":
                assert r["label"].lower() in {catalog.careers and d for d in snap.interests} or r["label"].lower().replace(" ", "") in snap.interests


def test_hallucination_rate(catalog):
    """No recommendation may reference a skill, career, project or certificate outside the knowledge base,
    and roadmap steps must be justified by the target career's requirements or their prerequisites."""
    violations = total = 0
    for p in PERSONAS:
        snap = _snap(catalog, p)
        for m in discover(snap, catalog, limit=3):
            career = catalog.careers[m["career_id"]]
            gap = analyze_gap(snap, career, catalog)
            projects = recommend_projects(snap, career, gap, catalog)
            rm = build_roadmap(snap, career, catalog, flagship=projects["flagship"])
            allowed = {r.skill_id for r in career.skills}
            allowed |= {pre for s in allowed for pre in catalog.skills[s].prereqs}
            for ph in rm["phases"]:
                for s in ph["steps"]:
                    total += 1
                    if s["skill_id"] and s["skill_id"] not in allowed:
                        violations += 1
                    if s["kind"] == "project" and s["content"]["project_id"] not in catalog.projects:
                        violations += 1
            for pr in projects["projects"]:
                total += 1
                violations += pr["id"] not in catalog.projects
    rate = violations / max(total, 1)
    print(f"\nHallucination rate={rate:.3f} over {total} generated items")
    assert rate == 0


def test_no_forbidden_claims(catalog):
    for p in PERSONAS:
        snap = _snap(catalog, p)
        for m in discover(snap, catalog, limit=5):
            text = " ".join([m["summary"], m["why_summary"], *[r["detail"] for r in m["reasons"]]])
            assert not FORBIDDEN_CLAIMS.search(text)


CITATION_QUERIES = [
    ("what does a data engineer do", "career:data-engineer"),
    ("how to learn kubernetes", "skill:kubernetes"),
    ("AWS solutions architect certification", "certificate:aws-solutions-architect-associate"),
    ("backtesting engine project for quant finance", "project:backtesting-engine"),
    ("explain retrieval augmented generation", "skill:rag"),
    ("penetration testing web security", "skill:penetration_testing"),
    ("UX research usability testing", "skill:ux_research"),
    ("FHIR healthcare data", "skill:healthcare_data"),
]


def test_citation_correctness():
    """Recall@5 of the expected source for each query, and every citation must resolve to a KB document."""
    r = get_retriever()
    found = 0
    for q, expected in CITATION_QUERIES:
        hits = r.search(q, k=5)
        ids = [h["id"] for h in hits]
        assert all(i in r.docs for i in ids)
        found += any(i.startswith(expected) for i in ids)
    recall = found / len(CITATION_QUERIES)
    print(f"\nCitation recall@5={recall:.2f}")
    assert recall >= 0.85


def test_career_resource_relevance(catalog, demo_snapshot):
    """Learning resources attached to each roadmap step must belong to that step's skill."""
    st = asyncio.run(run_pipeline(demo_snapshot, catalog, target_career_id="ai-engineer", enrich=False))
    for item in st["learning"]:
        skill = catalog.skills[item["skill_id"]]
        assert [r["title"] for r in item["learn"]] == [r.title for r in skill.learn]
        req = catalog.careers["ai-engineer"].requirement(item["skill_id"])
        assert req is not None
