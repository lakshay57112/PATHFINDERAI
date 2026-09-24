"""Unit tests: knowledge base, extraction, career matching, skill gaps, recommendations, roadmap, readiness."""
from app.engines.extraction import analyze_certificate, analyze_project, extract_job_description
from app.engines.matcher import compare, discover, skill_coverage
from app.engines.profile_analyzer import analyze_profile
from app.engines.readiness import readiness
from app.engines.recommendations import recommend_certificates, recommend_projects
from app.engines.roadmap import build_roadmap, weeks_range
from app.engines.skill_gap import analyze_gap, status_for
from app.knowledge.vocab import a_an
from tests.conftest import make_snapshot


# ---------------------------------------------------------------- knowledge base
def test_catalog_integrity(catalog):
    assert len(catalog.careers) >= 50
    assert len(catalog.skills) >= 90
    families = {c.family for c in catalog.careers.values()}
    assert {"technology", "data", "business", "finance", "marketing", "design", "healthcare", "research", "other"} <= families


def test_required_career_list_present(catalog):
    for cid in ["software-engineer", "ai-engineer", "ml-engineer", "genai-engineer", "data-engineer", "cloud-engineer",
                "devops-engineer", "mlops-engineer", "cybersecurity-engineer", "web-developer", "mobile-developer",
                "data-analyst", "data-scientist", "bi-analyst", "product-analyst", "analytics-engineer", "research-analyst",
                "business-analyst", "product-manager", "strategy-analyst", "operations-analyst", "management-consultant",
                "project-manager", "financial-analyst", "investment-analyst", "risk-analyst", "fintech-analyst",
                "quantitative-analyst", "financial-data-analyst", "digital-marketing-analyst", "growth-analyst",
                "marketing-analyst", "seo-specialist", "marketing-automation-specialist", "ux-designer", "ui-designer",
                "product-designer", "ux-researcher", "creative-technologist", "health-data-analyst",
                "health-informatics-specialist", "healthcare-ai-engineer", "bioinformatics-analyst", "research-scientist",
                "data-researcher", "computational-scientist", "entrepreneur", "technical-founder", "educator",
                "technical-writer", "solutions-architect", "sales-engineer", "customer-success-engineer"]:
        assert cid in catalog.careers, cid


def test_skill_extraction_handles_ambiguous_words(catalog):
    found = catalog.extract_skills("Built with Python, R, SQL; let's go to production with Docker on AWS")
    assert {"python", "r", "sql", "docker", "cloud"} <= set(found)
    assert "go" not in found  # "go to" is English, not Golang


def test_a_an():
    assert a_an("AI Engineer") == "an AI Engineer"
    assert a_an("UX Designer") == "a UX Designer"
    assert a_an("Data Scientist") == "a Data Scientist"


# ---------------------------------------------------------------- extraction
def test_project_analysis(catalog):
    a = analyze_project("RAG Chatbot", "Retrieval-augmented chatbot over PDFs with LangChain, embeddings and a vector store, returning cited sources.",
                        ["Python", "LangChain", "ChromaDB"], catalog)
    assert {"rag", "python", "vector_databases"} <= set(a["skill_ids"])
    assert a["career_relevance"], "should map to at least one career"


def test_certificate_analysis_uses_catalog(catalog):
    a = analyze_certificate("AWS Certified Solutions Architect Associate", "Amazon", "", catalog)
    assert a["catalog_id"] == "aws-solutions-architect-associate"
    assert "cloud_architecture" in a["skill_ids"]
    assert a["level"] == "associate"


def test_unknown_certificate_infers_from_text(catalog):
    a = analyze_certificate("Advanced Kubernetes Operations", "Some Academy", "Covers Helm, Docker and monitoring with Prometheus", catalog)
    assert {"kubernetes", "docker", "observability"} <= set(a["skill_ids"])
    assert a["level"] == "professional"


def test_job_description_extraction(catalog):
    ex = extract_job_description("ML Engineer", "- Build and deploy models with Python and Docker\n- 3+ years experience\n- Master's degree preferred\n"
                                 "AWS Certified Machine Learning Engineer is a plus", catalog)
    assert {"python", "docker"} <= set(ex["skills"])
    assert ex["min_years"] == 3
    assert "Master's degree" in ex["education"]
    assert "aws-ml-engineer-associate" in ex["certifications"]


# ---------------------------------------------------------------- profile + matching
def test_profile_scores_bounded_and_explained(catalog, demo_snapshot):
    p = analyze_profile(demo_snapshot, catalog)
    assert all(0 <= d["score"] <= 10 for d in p["domains"])
    top = [d["label"] for d in p["domains"][:3]]
    assert "AI" in top and "Technology" in top
    assert "not scientific" in p["disclaimer"]


def test_demo_user_discovers_expected_paths(catalog, demo_snapshot):
    names = [m["career_id"] for m in discover(demo_snapshot, catalog, limit=6)]
    assert names[0] in {"ai-engineer", "fintech-engineer"}
    assert {"ai-engineer", "ml-engineer", "data-scientist"} <= set(names)
    assert any(c in names for c in ("fintech-engineer", "financial-data-analyst"))


def test_every_match_is_explained_from_profile(catalog, demo_snapshot):
    for m in discover(demo_snapshot, catalog):
        assert m["reasons"], m["name"]
        assert all(r["source"] == "your_profile" for r in m["reasons"])
        assert m["why_summary"]


def test_discovery_is_diverse(catalog, demo_snapshot):
    fams = [catalog.careers[m["career_id"]].signals.domains for m in discover(demo_snapshot, catalog, limit=6)]
    primaries = [max(d, key=d.get) for d in fams]
    assert len(set(primaries)) >= 2


def test_designer_persona(catalog):
    snap = make_snapshot(catalog, interests=["design", "technology"], skills={"ui_design": "intermediate", "html_css": "beginner"},
                         activities=["designing", "people"], work_styles=["design_experiences", "create_products"])
    ids = [m["career_id"] for m in discover(snap, catalog, limit=5)]
    assert {"ux-designer", "ui-designer", "product-designer"} & set(ids[:3])


def test_compare(catalog, demo_snapshot):
    out = compare(["ai-engineer", "data-analyst"], catalog, demo_snapshot)
    ai, da = out["careers"]
    assert ai["dimensions"]["ai_ml"]["level"] > da["dimensions"]["ai_ml"]["level"]
    assert "your_coverage" in ai


# ---------------------------------------------------------------- gap analysis
def test_status_thresholds():
    assert status_for(0, 2) == "not_explored"
    assert status_for(1, 3) == "needs_development"
    assert status_for(2, 3) == "developing"
    assert status_for(3, 3) == "strong"


def test_gap_for_demo_ai_engineer(catalog, demo_snapshot):
    gap = analyze_gap(demo_snapshot, catalog.careers["ai-engineer"], catalog)
    assert {"Python", "RAG", "SQL"} <= set(gap["strengths"])
    assert gap["priority_gaps"]
    for i in gap["items"]:
        if i["status"] != "strong":
            e = i["explanation"]
            assert e["why_it_matters"] and e["what_to_learn"] and e["suggested_practice"]


# ---------------------------------------------------------------- recommendations
def test_certificates_never_recommend_what_user_holds(catalog):
    snap = make_snapshot(catalog, interests=["cloud"], skills={"linux": "beginner"},
                         certificates=[{"name": "AWS Certified Cloud Practitioner", "issuer": "AWS"}])
    recs = recommend_certificates(snap, catalog.careers["cloud-engineer"], analyze_gap(snap, catalog.careers["cloud-engineer"], catalog), catalog)
    assert "aws-cloud-practitioner" not in [r["id"] for r in recs["recommendations"]]
    assert len(recs["recommendations"]) <= 3
    assert all(r["why"] and r["expected_benefit"] and r["time_required"] for r in recs["recommendations"])


def test_certificate_explains_overlap(catalog, demo_snapshot):
    career = catalog.careers["ai-engineer"]
    recs = recommend_certificates(demo_snapshot, career, analyze_gap(demo_snapshot, career, catalog), catalog)
    consider = [r for r in recs["recommendations"] if r["verdict"] == "consider"]
    for r in consider:
        assert "already demonstrates" in r["why"] and "project may provide stronger" in r["why"]


def test_projects_close_gaps_and_are_personalised(catalog, demo_snapshot):
    career = catalog.careers["ai-engineer"]
    gap = analyze_gap(demo_snapshot, career, catalog)
    recs = recommend_projects(demo_snapshot, career, gap, catalog)
    assert 1 <= len(recs["projects"]) <= 3
    gap_names = {i["name"] for i in gap["items"] if i["status"] != "strong"}
    for p in recs["projects"]:
        assert set(p["evidence"]["gaps_covered"]) & gap_names
        for field in ("problem", "why_it_fits", "architecture", "expected_output", "portfolio_value", "estimated_time"):
            assert p[field]
    assert sum(p["suggested_start"] for p in recs["projects"]) == 1


# ---------------------------------------------------------------- roadmap
def test_roadmap_skips_known_skills(catalog, demo_snapshot):
    career = catalog.careers["ai-engineer"]
    rm = build_roadmap(demo_snapshot, career, catalog)
    titles = [s["skill_id"] for ph in rm["phases"] for s in ph["steps"]]
    assert "python" not in titles  # advanced already — no beginner Python curriculum
    covered = [c["skill_id"] for ph in rm["phases"] for c in ph["covered"]]
    assert "python" in covered and "rag" in covered


def test_roadmap_starts_partial_skills_at_current_level(catalog, demo_snapshot):
    rm = build_roadmap(demo_snapshot, catalog.careers["ai-engineer"], catalog)
    ml = next(s for ph in rm["phases"] for s in ph["steps"] if s["skill_id"] == "machine_learning")
    assert ml["from_level"] == 2 and ml["target_level"] == 3
    assert "→" in ml["title"]


def test_roadmap_inserts_missing_prerequisites(catalog):
    snap = make_snapshot(catalog, interests=["cloud"], skills={})
    rm = build_roadmap(snap, catalog.careers["mlops-engineer"], catalog)
    order = [s["skill_id"] for ph in rm["phases"] for s in ph["steps"]]
    assert order.index("linux") < order.index("docker")
    assert order.index("docker") < order.index("kubernetes")


def test_roadmap_scales_with_hours(catalog, demo_snapshot):
    career = catalog.careers["ai-engineer"]
    slow = build_roadmap(demo_snapshot, career, catalog, hours_per_week=5)
    fast = build_roadmap(demo_snapshot, career, catalog, hours_per_week=20)
    assert slow["remaining_weeks_max"] > fast["remaining_weeks_max"] * 3
    assert slow["total_hours"] == fast["total_hours"]


def test_roadmap_only_contains_valid_skills(catalog, demo_snapshot):
    career = catalog.careers["data-scientist"]
    rm = build_roadmap(demo_snapshot, career, catalog)
    allowed = {r.skill_id for r in career.skills}
    allowed |= {p for s in allowed for p in catalog.skills[s].prereqs}
    for ph in rm["phases"]:
        for s in ph["steps"]:
            if s["skill_id"]:
                assert s["skill_id"] in allowed


def test_weeks_range():
    assert weeks_range(0, 10)[2] == "Already covered"
    lo, hi, _ = weeks_range(40, 10)
    assert lo <= 4 <= hi


# ---------------------------------------------------------------- readiness
def test_readiness_is_evidence_based(catalog, demo_snapshot):
    r = readiness(demo_snapshot, catalog.careers["ai-engineer"], catalog)
    assert set(r["buckets"]) == {"strong", "developing", "limited"}
    assert "deployment" in r["next_step"]
    assert "%" not in r["next_step"]


def test_skill_coverage_bounds(catalog, demo_snapshot):
    for c in catalog.careers.values():
        assert 0 <= skill_coverage(demo_snapshot, c) <= 1
