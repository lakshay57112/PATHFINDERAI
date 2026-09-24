"""Shared fixtures. Tests run fully offline: SQLite, embedded Qdrant, in-memory graph, no LLM."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="pathfinder-test-")
os.environ.update({
    "DATABASE_URL": os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db"),
    "ENVIRONMENT": "test",
    "LLM_PROVIDER": "none",
    "OPENAI_API_KEY": "",
    "GEMINI_API_KEY": "",
    "EMBEDDING_PROVIDER": "hash",
    "REDIS_URL": os.environ.get("TEST_REDIS_URL", ""),
    "QDRANT_URL": "",
    "NEO4J_URI": "",
    "UPLOAD_DIR": f"{_tmp}/uploads",
    "RATE_LIMIT_AI_PER_MINUTE": "1000",
    "RATE_LIMIT_AUTH_PER_MINUTE": "1000",
})

import pytest  # noqa: E402
import yaml  # noqa: E402

from app.engines.extraction import analyze_certificate, analyze_project  # noqa: E402
from app.engines.snapshot import ProfileSnapshot, SkillState, attach_evidence  # noqa: E402
from app.knowledge.catalog import get_catalog  # noqa: E402
from app.knowledge.vocab import LEVEL_FROM_LABEL  # noqa: E402


@pytest.fixture(scope="session")
def catalog():
    return get_catalog()


def make_snapshot(catalog, *, interests, skills, activities=(), work_styles=(), projects=(), certificates=(), hours=10, unsure=()):
    snap = ProfileSnapshot(user_id="test", name="Test", interests=list(interests), activities=list(activities),
                           work_styles=list(work_styles), hours_per_week=hours, experience_level="student")
    for sid, lvl in skills.items():
        snap.skills[sid] = SkillState(sid, LEVEL_FROM_LABEL[lvl])
    for sid in unsure:
        snap.skills[sid] = SkillState(sid, 0, True)
    for p in projects:
        a = analyze_project(p["name"], p["description"], p.get("technologies", []), catalog)
        snap.projects.append({"id": p["name"], "name": p["name"], "skills": a["skill_ids"], "domains": a["domains"], "status": "completed"})
    for c in certificates:
        a = analyze_certificate(c["name"], c.get("issuer"), "", catalog)
        snap.certificates.append({"id": c["name"], "name": c["name"], "catalog_id": a["catalog_id"], "skills": a["skill_ids"]})
    return attach_evidence(snap, catalog)


@pytest.fixture
def demo_snapshot(catalog):
    from app.core.config import get_settings

    d = yaml.safe_load((get_settings().data_dir / "demo_user.yaml").read_text())
    return make_snapshot(catalog, interests=d["interests"], skills=d["skills"], activities=d["activities"],
                         work_styles=d["work_styles"], projects=d["projects"], certificates=d["certificates"],
                         hours=d["hours_per_week"], unsure=d.get("unsure", []))


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
