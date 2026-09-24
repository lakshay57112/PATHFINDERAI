"""LangGraph multi-agent pipeline.

    Profile Analyzer → Career Discovery → Career Research ─┬─(no target)→ END
                                                           └─(target)→ Skill Gap → Learning Recommendation
                                                                       → Certificate → Project Recommendation → Roadmap → END

Each agent runs a deterministic engine first. When an LLM is configured, agents may *enrich*
explanations through validated structured outputs (``app.ai.schemas`` + ``app.ai.guards``).
Agents never write to the database; the service layer persists validated results.
"""
from __future__ import annotations

import logging
import time
from typing import Any, TypedDict

from app.ai.guards import safe_text
from app.ai.llm import get_llm, try_structured
from app.ai.schemas import DiscoveryNarrative
from app.engines.matcher import discover
from app.engines.profile_analyzer import analyze_profile
from app.engines.recommendations import learning_plan_for_skill, recommend_certificates, recommend_projects
from app.engines.roadmap import build_roadmap
from app.engines.skill_gap import analyze_gap
from app.engines.snapshot import ProfileSnapshot
from app.graphdb.store import get_graph
from app.knowledge.catalog import Catalog
from app.rag.retriever import get_retriever

log = logging.getLogger("pathfinder.pipeline")


class PipelineState(TypedDict, total=False):
    snapshot: ProfileSnapshot
    catalog: Catalog
    target_career_id: str | None
    limit: int
    enrich: bool
    profile: dict
    matches: list[dict]
    research: dict
    gap: dict
    learning: list[dict]
    certificates: dict
    projects: dict
    roadmap: dict
    trace: list[dict]
    ai_used: bool


def _traced(name: str):
    def wrap(fn):
        async def node(state: PipelineState) -> dict:
            t0 = time.perf_counter()
            out = await fn(state)
            out["trace"] = [*state.get("trace", []), {"agent": name, "ms": round((time.perf_counter() - t0) * 1000, 1)}]
            return out
        node.__name__ = fn.__name__
        return node
    return wrap


@_traced("Profile Analyzer")
async def profile_analyzer(state: PipelineState) -> dict:
    return {"profile": analyze_profile(state["snapshot"], state["catalog"])}


@_traced("Career Discovery Agent")
async def career_discovery(state: PipelineState) -> dict:
    matches = discover(state["snapshot"], state["catalog"], limit=state.get("limit", 6))
    ai_used = state.get("ai_used", False)
    if state.get("enrich") and get_llm().available and matches:
        snap, cat = state["snapshot"], state["catalog"]
        profile_facts = (
            f"Interests: {', '.join(snap.interests)}. Enjoys: {', '.join(snap.activities)}. Work styles: {', '.join(snap.work_styles)}. "
            f"Skills: {', '.join(f'{cat.skill_name(k)} (level {v.level}/3)' for k, v in snap.skills.items() if v.level)}. "
            f"Projects: {', '.join(p['name'] for p in snap.projects)}."
        )
        options = "\n".join(f"- {m['career_id']}: {m['name']} — {m['summary']} Signals: {m['why_summary']}" for m in matches)
        narrative = await try_structured(
            "You explain career-path suggestions. Use ONLY the user's stated facts and the career summaries given. "
            "Never claim a path is objectively best, never guarantee jobs or salaries, never invent requirements. "
            "Write warmly and concisely in second person.",
            f"User profile:\n{profile_facts}\n\nSuggested paths:\n{options}\n\nWrite a one-sentence intro and a 2-sentence "
            "explanation per career id.",
            DiscoveryNarrative,
        )
        if narrative:
            by_id = {c.career_id: safe_text(c.explanation, 420) for c in narrative.careers}
            for m in matches:
                if by_id.get(m["career_id"]):  # unknown ids are ignored by construction
                    m["ai_explanation"] = by_id[m["career_id"]]
            ai_used = True
    return {"matches": matches, "ai_used": ai_used}


@_traced("Career Research Agent")
async def career_research(state: PipelineState) -> dict:
    """Pull supporting knowledge (RAG) and relationships (graph) for the top paths."""
    retriever, graph, cat = get_retriever(), get_graph(), state["catalog"]
    research: dict[str, Any] = {}
    focus = [state["target_career_id"]] if state.get("target_career_id") else [m["career_id"] for m in state.get("matches", [])[:3]]
    for cid in focus:
        career = cat.careers[cid]
        hits = retriever.search(f"{career.name} role skills entry routes", k=3, types=["career"])
        research[cid] = {
            "sources": [{k: h[k] for k in ("id", "title", "type", "source", "url")} for h in hits],
            "related_careers": [{"id": r, "name": cat.careers[r].name} for r in graph.related_careers(cid) if r in cat.careers],
        }
    return {"research": research}


@_traced("Skill Gap Agent")
async def skill_gap(state: PipelineState) -> dict:
    career = state["catalog"].careers[state["target_career_id"]]
    return {"gap": analyze_gap(state["snapshot"], career, state["catalog"])}


@_traced("Learning Recommendation Agent")
async def learning_recommendation(state: PipelineState) -> dict:
    cat, snap = state["catalog"], state["snapshot"]
    career = cat.careers[state["target_career_id"]]
    items = [i for i in state["gap"]["items"] if i["status"] != "strong"][:8]
    return {"learning": [learning_plan_for_skill(i["skill_id"], cat, from_level=i["current_level"], to_level=i["target_level"], career=career)
                         for i in items]}


@_traced("Certificate Agent")
async def certificate_agent(state: PipelineState) -> dict:
    career = state["catalog"].careers[state["target_career_id"]]
    return {"certificates": recommend_certificates(state["snapshot"], career, state["gap"], state["catalog"])}


@_traced("Project Recommendation Agent")
async def project_agent(state: PipelineState) -> dict:
    career = state["catalog"].careers[state["target_career_id"]]
    return {"projects": recommend_projects(state["snapshot"], career, state["gap"], state["catalog"])}


@_traced("Roadmap Agent")
async def roadmap_agent(state: PipelineState) -> dict:
    career = state["catalog"].careers[state["target_career_id"]]
    return {"roadmap": build_roadmap(state["snapshot"], career, state["catalog"], flagship=state["projects"]["flagship"])}


def _route_after_research(state: PipelineState) -> str:
    return "skill_gap" if state.get("target_career_id") else "__end__"


def build_graph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:  # pragma: no cover
        return None
    g = StateGraph(PipelineState)
    g.add_node("profile_analyzer", profile_analyzer)
    g.add_node("career_discovery", career_discovery)
    g.add_node("career_research", career_research)
    g.add_node("skill_gap", skill_gap)
    g.add_node("learning_recommendation", learning_recommendation)
    g.add_node("certificate_agent", certificate_agent)
    g.add_node("project_agent", project_agent)
    g.add_node("roadmap_agent", roadmap_agent)
    g.add_edge(START, "profile_analyzer")
    g.add_edge("profile_analyzer", "career_discovery")
    g.add_edge("career_discovery", "career_research")
    g.add_conditional_edges("career_research", _route_after_research, {"skill_gap": "skill_gap", "__end__": END})
    g.add_edge("skill_gap", "learning_recommendation")
    g.add_edge("learning_recommendation", "certificate_agent")
    g.add_edge("certificate_agent", "project_agent")
    g.add_edge("project_agent", "roadmap_agent")
    g.add_edge("roadmap_agent", END)
    return g.compile()


_compiled = None


async def run_pipeline(snapshot: ProfileSnapshot, catalog: Catalog, *, target_career_id: str | None = None,
                       limit: int = 6, enrich: bool = True) -> PipelineState:
    global _compiled
    state: PipelineState = {"snapshot": snapshot, "catalog": catalog, "target_career_id": target_career_id,
                            "limit": limit, "enrich": enrich, "trace": [], "ai_used": False}
    if _compiled is None:
        _compiled = build_graph()
    if _compiled is not None:
        return await _compiled.ainvoke(state)
    # Sequential fallback with identical semantics
    for node in (profile_analyzer, career_discovery, career_research):
        state.update(await node(state))
    if target_career_id:
        for node in (skill_gap, learning_recommendation, certificate_agent, project_agent, roadmap_agent):
            state.update(await node(state))
    return state
