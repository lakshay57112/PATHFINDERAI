"""Unit tests for RAG fusion, guards, interview rubric, mentor intent routing and the LangGraph pipeline."""
import asyncio

from app.ai.guards import hallucinated_skill_mentions, safe_text, valid_skill_ids
from app.ai.interview import evaluate_offline
from app.ai.pipeline import run_pipeline
from app.rag.embeddings import HashEmbedder
from app.rag.retriever import get_retriever, rrf
from app.services.mentor_service import detect_intent


def test_rrf_rewards_agreement():
    scores = rrf([["a", "b", "c"], ["b", "a", "d"]])
    assert scores["a"] > scores["c"] and scores["b"] > scores["d"]


def test_hash_embedder_is_deterministic_and_normalised():
    e = HashEmbedder()
    v1, v2 = e.embed(["retrieval augmented generation", "retrieval augmented generation"])
    assert v1 == v2
    assert abs(sum(x * x for x in v1) - 1) < 1e-6


def test_hybrid_search_finds_relevant_docs():
    r = get_retriever()
    hits = r.search("how do I learn docker containers", k=3)
    assert hits[0]["title"].startswith("Docker")
    assert all(h["source"] for h in hits)
    cert_hits = r.search("AWS machine learning certification", k=3, types=["certificate"])
    assert all(h["type"] == "certificate" for h in cert_hits)
    assert "AWS" in cert_hits[0]["title"]


def test_guards(catalog):
    assert valid_skill_ids(["python", "made_up_skill", "python"], catalog) == ["python"]
    assert safe_text("This path will guarantee a job for you.") is None
    assert safe_text("This path may suit your interest in data.")
    assert hallucinated_skill_mentions("Learn Docker and Kubernetes", {"docker"}, catalog) == ["kubernetes"]


def test_interview_offline_rubric(catalog):
    q = catalog.questions["rag-how"]
    strong = evaluate_offline(q, "First we chunk and ingest documents, create embeddings in a vector store, retrieve the top-k relevant "
                                 "chunks, add them as context to the prompt, and the LLM answers grounded in sources with citations. "
                                 "Then we evaluate recall and faithfulness with metrics.")
    weak = evaluate_offline(q, "It uses AI.")
    assert strong["technical_coverage"] >= 80 > weak["technical_coverage"]
    assert weak["missing_concepts"] and strong["accuracy"] == "not_assessed"


def test_mentor_intents():
    assert detect_intent("I only have 5 hours this week. Adjust my roadmap.", False) == "adjust_hours"
    assert detect_intent("I already know Docker", False) == "known_skill"
    assert detect_intent("Quiz me", False) == "quiz"
    assert detect_intent("some answer text", True) == "quiz_answer"
    assert detect_intent("What should I learn next?", False) == "next_step"
    assert detect_intent("Give me a project", False) == "project"
    assert detect_intent("Am I ready for the next phase?", False) == "readiness"
    assert detect_intent("Explain RAG", False) == "explain"
    assert detect_intent("I want to switch to Data Scientist", False) == "change_career"


def test_langgraph_pipeline_runs_all_agents(catalog, demo_snapshot):
    st = asyncio.run(run_pipeline(demo_snapshot, catalog, target_career_id="ai-engineer"))
    agents = [t["agent"] for t in st["trace"]]
    assert agents == ["Profile Analyzer", "Career Discovery Agent", "Career Research Agent", "Skill Gap Agent",
                      "Learning Recommendation Agent", "Certificate Agent", "Project Recommendation Agent", "Roadmap Agent"]
    assert st["roadmap"]["phases"] and st["research"]["ai-engineer"]["sources"]


def test_pipeline_stops_after_research_without_target(catalog, demo_snapshot):
    st = asyncio.run(run_pipeline(demo_snapshot, catalog))
    assert len(st["trace"]) == 3 and "roadmap" not in st
