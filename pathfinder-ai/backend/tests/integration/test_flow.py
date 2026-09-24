"""Integration: Profile → Career discovery → Career selection → Gap analysis → Roadmap → Adaptation, plus privacy."""
import io
import json
import uuid

from fastapi.testclient import TestClient


def _register(client: TestClient, name="Test User") -> dict:
    client.cookies.clear()
    r = client.post("/api/v1/auth/register", json={"email": f"{uuid.uuid4().hex[:8]}@example.com", "password": "password123", "name": name})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


ONBOARDING = {
    "interests": ["ai", "technology", "finance"],
    "skills": [{"skill_id": "python", "level": "advanced"}, {"skill_id": "sql", "level": "intermediate"},
               {"skill_id": "machine_learning", "level": "intermediate"}, {"skill_id": "docker", "level": "unsure"}],
    "activities": ["building", "analyzing_data"],
    "work_styles": ["build_software", "work_with_data"],
    "hours_per_week": 10,
    "projects": [{"name": "Fraud Detection", "description": "Imbalanced classification with scikit-learn and XGBoost", "technologies": ["Python", "XGBoost"]}],
    "certificates": [{"name": "Machine Learning Specialization", "issuer": "Coursera"}],
}


def test_full_journey(client):
    h = _register(client)
    assert client.get("/api/v1/auth/me", headers=h).json()["onboarding_completed"] is False

    r = client.post("/api/v1/profile", json=ONBOARDING, headers=h)
    assert r.status_code == 200
    prof = r.json()
    assert prof["onboarding_completed"] and len(prof["projects"]) == 1 and len(prof["certificates"]) == 1
    assert prof["certificates"][0]["catalog_id"] == "dlai-ml-specialization"

    analysis = client.get("/api/v1/profile/analysis", headers=h).json()
    assert analysis["domains"] and "Python" in [s["name"] for s in analysis["current_strengths"]]

    disc = client.post("/api/v1/career/discover", json={}, headers=h).json()
    ids = [m["career_id"] for m in disc["matches"]]
    assert "ai-engineer" in ids
    assert [t["agent"] for t in disc["trace"]][:2] == ["Profile Analyzer", "Career Discovery Agent"]

    # Gap analysis requires a target
    assert client.get("/api/v1/gap-analysis", headers=h).json()["error"]["code"] == "no_target_career"
    assert client.post("/api/v1/career/select", json={"career_id": "ai-engineer"}, headers=h).status_code == 200
    gap = client.get("/api/v1/gap-analysis", headers=h).json()
    assert "Python" in gap["strengths"]

    rm = client.post("/api/v1/roadmap/generate", json={"hours_per_week": 10}, headers=h).json()
    assert rm["career_id"] == "ai-engineer" and rm["phases"][-1]["name"] == "Portfolio"
    all_steps = [s for ph in rm["phases"] for s in ph["steps"]]
    assert "python" not in [s["skill_id"] for s in all_steps]

    # Complete a step → skill level rises and evidence is recorded
    step = next(s for s in all_steps if s["kind"] == "skill")
    rm2 = client.patch(f"/api/v1/roadmap/steps/{step['id']}", json={"status": "done", "evidence_url": "https://github.com/x/y"}, headers=h).json()
    assert rm2["skills_done"] == 1
    prog = client.get("/api/v1/progress", headers=h).json()
    assert any(e["kind"] == "skill" and e["url"] == "https://github.com/x/y" for e in prog["evidence"])
    assert prog["skills"]["done"] == 1

    # Adapt: fewer hours → longer timeline; "I already know Docker" → skipped
    before = rm2["remaining_weeks_max"]
    rm3 = client.post("/api/v1/roadmap/adjust", json={"hours_per_week": 4}, headers=h).json()
    assert rm3["remaining_weeks_max"] > before
    rm4 = client.post("/api/v1/roadmap/adjust", json={"known_skills": ["docker"]}, headers=h).json()
    docker = [s for ph in rm4["phases"] for s in ph["steps"] if s["skill_id"] == "docker"]
    assert all(s["status"] == "skipped" for s in docker)
    assert rm4["applied_known"] == ["Docker"]

    # Switch career → recalculated, completed work carried over
    completed_skill = step["skill_id"]
    rm5 = client.post("/api/v1/roadmap/generate", json={"career_id": "data-scientist"}, headers=h).json()
    assert rm5["switched_from"] == "AI Engineer" and rm5["version"] == 2
    ds_ids = [s["skill_id"] for ph in rm5["phases"] for s in ph["steps"] if s["status"] != "skipped"]
    assert completed_skill not in ds_ids or catalog_target_exceeds(completed_skill)

    recs = client.post("/api/v1/recommendations", json={}, headers=h).json()
    assert recs["projects"]["projects"] and "principle" in recs["certificates"]

    dash = client.get("/api/v1/dashboard", headers=h).json()
    assert dash["target"]["id"] == "data-scientist" and dash["insights"]["projects_recommended"] >= 1


def catalog_target_exceeds(skill_id: str) -> bool:
    # A completed AI-Engineer step may still appear if Data Scientist needs a higher level.
    from app.knowledge.catalog import get_catalog

    ds = get_catalog().careers["data-scientist"].requirement(skill_id)
    return bool(ds and ds.level >= 2)


def test_mentor_streams_and_adapts_roadmap(client):
    h = _register(client)
    client.post("/api/v1/profile", json=ONBOARDING, headers=h)
    client.post("/api/v1/roadmap/generate", json={"career_id": "ai-engineer"}, headers=h)

    def chat(msg, sid=None):
        r = client.post("/api/v1/mentor/chat", json={"message": msg, "session_id": sid}, headers=h)
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
        events = [(b.split("\n")[0][7:], json.loads(b.split("\n")[1][6:])) for b in r.text.strip().split("\n\n")]
        meta = events[0][1]
        text = "".join(d["t"] for e, d in events if e == "token")
        assert events[-1][0] == "done"
        return meta, text

    meta, text = chat("What should I learn next?")
    assert meta["intent"] == "next_step" and "Next up" in text
    assert all(s["type"] in {"career", "skill", "resource", "certificate", "project", "interview"} for s in meta["sources"])

    meta, text = chat("I only have 5 hours this week. Adjust my roadmap.", meta["session_id"])
    assert meta["action"]["type"] == "roadmap_updated"
    assert client.get("/api/v1/roadmap", headers=h).json()["hours_per_week"] == 5

    meta, text = chat("Quiz me", meta["session_id"])
    assert meta["intent"] == "quiz"
    meta, text = chat("First chunk documents, embed them in a vector database, retrieve top-k relevant context, "
                      "add it to the prompt so the LLM answers grounded in sources with citations, then evaluate recall.", meta["session_id"])
    assert meta["intent"] == "quiz_answer" and "coverage" in text.lower()


def test_interview_mode(client):
    h = _register(client)
    client.post("/api/v1/profile", json=ONBOARDING, headers=h)
    client.post("/api/v1/career/select", json={"career_id": "ai-engineer"}, headers=h)
    s = client.post("/api/v1/interview/start", json={"mode": "technical"}, headers=h).json()
    assert s["question"]["number"] == 1
    a = client.post("/api/v1/interview/answer", json={"session_id": s["session_id"], "answer": "It is about search."}, headers=h).json()
    ev = a["evaluation"]
    assert {"technical_coverage", "accuracy", "clarity", "missing_concepts"} <= set(ev)
    assert a["next_question"]["is_follow_up"] is True


def test_market_intelligence_labels_sources(client):
    h = _register(client)
    client.post("/api/v1/profile", json=ONBOARDING, headers=h)
    d = client.post("/api/v1/market/analyze", json={"career_id": "ai-engineer"}, headers=h).json()
    assert d["sample_size"] > 0 and d["period"] and d["sources"]
    assert d["synthetic_only"] is True and any("synthetic" in x.lower() for x in d["disclaimers"])
    r = client.post("/api/v1/market/ingest", headers=h, json={"source": "Test paste", "career_id": "ai-engineer", "postings": [
        {"title": "AI Engineer", "description": "Build RAG systems with Python, LangChain and Qdrant. Deploy with Docker and Kubernetes. 2+ years."}]})
    assert r.json()["status"] == "completed"
    d2 = client.post("/api/v1/market/analyze", json={"career_id": "ai-engineer", "include_synthetic": False}, headers=h).json()
    assert d2["sample_size"] == 1 and d2["sources"][0]["yours"]


def test_user_data_isolation(client):
    a = _register(client, "Alice")
    client.post("/api/v1/profile", json=ONBOARDING, headers=a)
    rm = client.post("/api/v1/roadmap/generate", json={"career_id": "ai-engineer"}, headers=a).json()
    step_id = rm["phases"][0]["steps"][0]["id"]
    proj_id = client.get("/api/v1/profile", headers=a).json()["projects"][0]["id"]

    b = _register(client, "Bob")
    assert client.patch(f"/api/v1/roadmap/steps/{step_id}", json={"status": "done"}, headers=b).status_code == 404
    assert client.delete(f"/api/v1/projects/{proj_id}", headers=b).status_code == 404
    assert client.get("/api/v1/profile", headers=b).json()["projects"] == []
    # Private job postings are not visible to others
    client.post("/api/v1/market/ingest", headers=a, json={"source": "Alice private", "postings": [{"title": "AI Engineer", "description": "Python and RAG and Docker required, 3 years."}]})
    d = client.post("/api/v1/market/analyze", json={"career_id": "ai-engineer", "include_synthetic": False}, headers=b).json()
    assert d["sample_size"] == 0


def test_auth_errors_and_validation(client):
    client.cookies.clear()
    assert client.get("/api/v1/profile").status_code == 401
    r = client.post("/api/v1/auth/register", json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    h = _register(client)
    bad = client.post("/api/v1/profile", json={"interests": ["astrology"]}, headers=h)
    assert bad.status_code == 422
    assert client.get("/api/v1/careers/not-a-career").json()["error"]["code"] == "not_found"
    assert "Traceback" not in bad.text


def test_secure_upload(client):
    h = _register(client)
    bad = client.post("/api/v1/certificates/upload", headers=h, data={"name": "Fake"}, files={"file": ("x.pdf", io.BytesIO(b"MZ\x90 not a pdf"), "application/pdf")})
    assert bad.status_code == 415 and bad.json()["error"]["code"] == "invalid_file"
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    ok = client.post("/api/v1/certificates/upload", headers=h, data={"name": "CompTIA Security+", "issuer": "CompTIA"},
                     files={"file": ("cert.png", io.BytesIO(png), "image/png")})
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["has_file"] and body["catalog_id"] == "comptia-security-plus"


def test_export_and_delete_account(client):
    h = _register(client)
    client.post("/api/v1/profile", json=ONBOARDING, headers=h)
    exp = client.get("/api/v1/account/export", headers=h)
    assert exp.status_code == 200 and exp.json()["profile"]["interests"] == ["ai", "technology", "finance"]
    assert client.delete("/api/v1/account", headers=h).json()["ok"] is True
    assert client.get("/api/v1/profile", headers=h).status_code == 401


def test_demo_account(client):
    client.cookies.clear()
    r = client.post("/api/v1/auth/demo")
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    dash = client.get("/api/v1/dashboard", headers=h).json()
    assert dash["target"]["name"] == "AI Engineer" and dash["has_roadmap"]
    assert client.delete("/api/v1/account", headers=h).status_code == 403
