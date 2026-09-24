"""AI Career Mentor.

A tool-using mentor: it detects what the user wants, runs deterministic tools against their
profile/roadmap (which may *adapt* the roadmap), retrieves knowledge-base context with
citations, and then answers — streamed from the LLM when configured, or composed from the
tool results offline. Tools are the only way the mentor changes user data.
"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator

from sqlalchemy.orm import Session

from app.ai.guards import safe_text
from app.ai.interview import evaluate
from app.ai.llm import get_llm
from app.core.errors import AppError, NotFound
from app.db.models import ChatMessage, ChatSession, Progress, User
from app.engines.extraction import analyze_project
from app.engines.readiness import readiness
from app.engines.recommendations import recommend_projects
from app.engines.skill_gap import analyze_gap
from app.knowledge.catalog import Catalog
from app.knowledge.vocab import LEVELS, a_an
from app.rag.retriever import get_retriever
from app.services import roadmap_service as rs
from app.services.profile_service import build_snapshot, get_or_create_profile

SUGGESTIONS = [
    "What should I learn next?",
    "Explain RAG evaluation",
    "Give me a project",
    "Review my project",
    "Quiz me",
    "Am I ready for the next phase?",
    "I only have 5 hours this week. Adjust my roadmap.",
]

HOURS_RE = re.compile(r"\b(\d{1,2})\s*(?:hours?|hrs?|h)\b", re.I)


def detect_intent(text: str, has_pending_quiz: bool) -> str:
    t = text.lower().strip()
    if HOURS_RE.search(t) and re.search(r"\b(week|weekly|per week|a week|this week|only have|adjust)\b", t):
        return "adjust_hours"
    if re.search(r"\b(already know|i know|i'?m (?:comfortable|good|confident) (?:with|at|in)|skip)\b", t):
        return "known_skill"
    if re.search(r"\b(switch|change|move|pivot)\b.*\b(to|into|towards)\b", t) and re.search(r"career|role|path|to\b", t):
        return "change_career"
    if re.search(r"\bquiz\b|\btest me\b|\bask me a question\b", t):
        return "quiz"
    if has_pending_quiz:
        return "quiz_answer"
    if re.search(r"\breview\b.*\bproject\b|\bfeedback on my project\b|github\.com/", t):
        return "review_project"
    if re.search(r"\b(am i ready|ready for|readiness)\b", t):
        return "readiness"
    if re.search(r"\b(give me|suggest|recommend|idea for)\b.*\bproject|\bproject idea", t):
        return "project"
    if re.search(r"\b(what should i (learn|do|focus|study)|next step|what'?s next|learn next)\b", t):
        return "next_step"
    if re.search(r"\b(explain|what is|what are|tell me about|how does|how do)\b", t):
        return "explain"
    return "general"


def _find_career(text: str, catalog: Catalog) -> str | None:
    t = text.lower()
    best = None
    for c in catalog.careers.values():
        names = {c.name.lower(), c.id.replace("-", " "), c.name.lower().split(" (")[0]}
        for n in names:
            if n in t and (best is None or len(n) > best[1]):
                best = (c.id, len(n))
    return best[0] if best else None


class MentorContext:
    def __init__(self, db: Session, user: User, catalog: Catalog):
        self.db, self.user, self.catalog = db, user, catalog
        self.profile = get_or_create_profile(db, user)
        self.snapshot = build_snapshot(db, user, catalog)
        self.rm = rs.active_roadmap(db, user)
        self.rm_data = rs.serialize_roadmap(self.rm, catalog) if self.rm else None
        cid = self.profile.target_career_id
        self.career = catalog.careers.get(cid) if cid else None

    def summary(self) -> str:
        cat, s = self.catalog, self.snapshot
        skills = ", ".join(f"{cat.skill_name(k)} ({LEVELS[v.level].lower()})" for k, v in sorted(s.skills.items(), key=lambda kv: -kv[1].level) if v.level)[:600]
        lines = [f"Name: {self.user.name or 'the user'}",
                 f"Interests: {', '.join(s.interests) or 'not stated'}",
                 f"Skills (user-provided): {skills or 'none yet'}",
                 f"Projects: {', '.join(p['name'] for p in s.projects) or 'none'}",
                 f"Hours per week: {s.hours_per_week}",
                 f"Target career: {self.career.name if self.career else 'not chosen yet'}"]
        if self.rm_data:
            nxt = rs.next_step(self.rm_data)
            lines.append(f"Roadmap: {self.rm_data['skills_done']}/{self.rm_data['skills_total']} skills done, remaining {self.rm_data['remaining_label']}")
            if nxt:
                lines.append(f"Next roadmap step: {nxt['title']} (phase: {nxt['phase_name']})")
        return "\n".join(lines)


# ------------------------------------------------------------------------ tools
def tool_next_step(ctx: MentorContext) -> dict:
    if not ctx.rm_data:
        return {"text": "You don't have a roadmap yet. Pick a direction on the Discover page and I'll build one around what you already know.",
                "query": "how to choose a career path"}
    nxt = rs.next_step(ctx.rm_data)
    if not nxt:
        return {"text": f"You've completed every required step on your {ctx.rm_data['career_name']} roadmap. "
                        "Now deepen your flagship project and practise interviews.", "query": ctx.rm_data["career_name"] + " interview"}
    c = nxt["content"]
    res = c.get("learn", [])[:2]
    lines = [f"**Next up: {nxt['title']}** — part of your *{nxt['phase_name']}* phase (~{nxt['est_hours']:.0f} hours, "
             f"about {max(1, round(nxt['est_hours'] / max(ctx.snapshot.hours_per_week, 1)))} week(s) at your pace)."]
    if res:
        lines.append("**Learn:** " + "; ".join(f"[{r['title']}]({r['url']})" if r.get("url") else r["title"] for r in res))
    if c.get("practice"):
        lines.append(f"**Practice:** {c['practice']}")
    if c.get("build"):
        lines.append(f"**Build:** {c['build']}")
    if c.get("prove"):
        lines.append(f"**Prove it:** {c['prove']}")
    return {"text": "\n\n".join(lines), "query": nxt["title"], "skill_ids": [nxt["skill_id"]] if nxt.get("skill_id") else []}


def tool_explain(ctx: MentorContext, message: str) -> dict:
    skills = ctx.catalog.extract_skills(message)
    if not skills:
        return {"text": None, "query": message}
    s = ctx.catalog.skills[skills[0]]
    you = ctx.snapshot.level(s.id)
    req = ctx.career.requirement(s.id) if ctx.career else None
    lines = [f"**{s.name}** — {s.description}"]
    if req:
        lines.append(f"For {a_an(ctx.career.name)}, it's {a_an('*' + req.importance + '*')} skill; the typical target is {LEVELS[req.level].lower()}. "
                     f"You're currently at: {LEVELS[you].lower()} (from your profile).")
    lines.append(f"**A good way to practise:** {s.practice}")
    if s.learn:
        r = s.learn[0]
        lines.append(f"**Start with:** [{r.title}]({r.url}) — {r.provider}")
    return {"text": "\n\n".join(lines), "query": f"{s.name} {message}", "skill_ids": [s.id]}


def tool_project(ctx: MentorContext) -> dict:
    if not ctx.career:
        return {"text": "Choose a target career first and I'll suggest projects that close your specific gaps.", "query": "portfolio projects"}
    gap = analyze_gap(ctx.snapshot, ctx.career, ctx.catalog)
    recs = recommend_projects(ctx.snapshot, ctx.career, gap, ctx.catalog)
    p = next((x for x in recs["projects"] if x.get("suggested_start")), None) or (recs["projects"][0] if recs["projects"] else None)
    if not p:
        return {"text": "I couldn't find a strong project match right now.", "query": ctx.career.name + " project"}
    text = (f"**{p['name']}** ({p['difficulty']}, {p['estimated_time']})\n\n**Problem:** {p['problem']}\n\n"
            f"**Why it fits you:** {p['why_it_fits']}\n\n**Architecture:** {' → '.join(p['architecture'])}\n\n"
            f"**Expected output:** {p['expected_output']}\n\n**Portfolio value:** {p['portfolio_value']}")
    return {"text": text, "query": p["name"], "skill_ids": p["skill_ids"]}


def tool_review_project(ctx: MentorContext, message: str) -> dict:
    projects = [p for p in ctx.user.projects]
    target = None
    for p in projects:
        if p.name.lower() in message.lower() or (p.github_url and p.github_url.lower() in message.lower()):
            target = p
    target = target or (projects[-1] if projects else None)
    if not target:
        return {"text": "Add a project on the Projects page (description, technologies, links) and I'll review it against your target career.",
                "query": "portfolio project review"}
    a = analyze_project(target.name, target.description, target.technologies or [], ctx.catalog)
    lines = [f"**Review: {target.name}**", f"Skills it demonstrates: {', '.join(x['name'] for x in a['skills_demonstrated']) or 'unclear from the description'}. "
             f"Estimated difficulty: {a['difficulty']}."]
    if ctx.career:
        core = [r for r in ctx.career.skills if r.importance in ("core", "important")]
        missing = [r for r in core if r.skill_id not in a["skill_ids"] and ctx.snapshot.level(r.skill_id) < r.level]
        if missing:
            lines.append(f"To make it stronger evidence for {a_an(ctx.career.name)}, consider extending it with "
                         f"{', '.join(ctx.catalog.skill_name(r.skill_id) for r in missing[:3])}.")
    checklist = []
    if not target.github_url:
        checklist.append("add a public repository link")
    if not target.demo_url:
        checklist.append("add a live demo or short video")
    if len(target.description or "") < 200:
        checklist.append("expand the description: problem, approach, results and what you'd improve")
    checklist.append("include an evaluation/results section with numbers")
    lines.append("**Checklist:** " + "; ".join(checklist) + ".")
    return {"text": "\n\n".join(lines), "query": target.name, "skill_ids": a["skill_ids"]}


def tool_readiness(ctx: MentorContext) -> dict:
    if not ctx.career:
        return {"text": "Pick a target career and I can show which areas have strong evidence and which don't yet.", "query": "career readiness"}
    r = readiness(ctx.snapshot, ctx.career, ctx.catalog)
    b = r["buckets"]
    lines = [f"Here's your current evidence for **{ctx.career.name}**:",
             f"- **Strong:** {', '.join(e['name'] for e in b['strong']) or '—'}",
             f"- **Developing:** {', '.join(e['name'] for e in b['developing']) or '—'}",
             f"- **Limited evidence:** {', '.join(e['name'] for e in b['limited']) or '—'}", "", r["next_step"]]
    if ctx.rm_data:
        cur = next((ph for ph in ctx.rm_data["phases"] if ph["status"] in ("todo", "in_progress")), None)
        if cur:
            pct = round(cur["progress"] * 100)
            lines.append(f"\nYour current phase, *{cur['name']}*, is {pct}% complete. "
                         + ("You look ready to move on once you've shipped evidence for it." if pct >= 75 else
                            "I'd finish its remaining steps before moving to the next phase."))
    return {"text": "\n".join(lines), "query": ctx.career.name + " skills"}


def tool_adjust_hours(ctx: MentorContext, message: str) -> dict:
    hours = int(HOURS_RE.search(message).group(1))
    hours = max(1, min(hours, 80))
    data = rs.set_hours(ctx.db, ctx.user, hours, ctx.catalog)
    if not data:
        return {"text": f"Noted — I've set your availability to {hours} hours per week. Your roadmap will be timed to that.",
                "action": {"type": "hours_updated", "hours_per_week": hours}}
    nxt = rs.next_step(data)
    focus = f" This week, focus on **{nxt['title']}** — aim for one small, finished piece of it." if nxt else ""
    return {"text": f"Done — I've re-timed your roadmap for **{hours} hours/week**. Remaining estimate: **{data['remaining_label']}**.{focus}",
            "action": {"type": "roadmap_updated", "reason": "hours", "hours_per_week": hours}}


def tool_known(ctx: MentorContext, message: str) -> dict:
    skills = ctx.catalog.extract_skills(message)
    if not skills:
        return {"text": "Which skill do you already know? For example: “I already know Docker.”"}
    _, applied = rs.mark_known(ctx.db, ctx.user, skills, ctx.catalog)
    return {"text": f"Got it — I've marked **{', '.join(applied)}** as known and skipped the fundamentals on your roadmap. "
                    "If you'd like to prove it, try “Quiz me” and I'll record it as evidence.",
            "action": {"type": "roadmap_updated", "reason": "known_skill", "skills": skills}}


def tool_change_career(ctx: MentorContext, message: str) -> dict:
    cid = _find_career(message, ctx.catalog)
    if not cid:
        return {"text": "Which career would you like to switch to? You can browse options on the Careers page."}
    old = ctx.career.name if ctx.career else None
    data = rs.generate_roadmap(ctx.db, ctx.user, ctx.catalog, career_id=cid)
    carried = data.get("carried_over") or []
    text = f"I've rebuilt your roadmap for **{data['career_name']}**" + (f" (previously {old})" if old else "") + ". "
    if carried:
        text += f"Completed work carried over: {', '.join(carried)}. "
    text += f"New remaining estimate: **{data['remaining_label']}**."
    return {"text": text, "action": {"type": "roadmap_updated", "reason": "career_change", "career_id": cid}}


def tool_quiz(ctx: MentorContext, session: ChatSession) -> dict:
    skill_ids = []
    if ctx.rm_data and (nxt := rs.next_step(ctx.rm_data)) and nxt.get("skill_id"):
        skill_ids.append(nxt["skill_id"])
    skill_ids += [k for k, v in sorted(ctx.snapshot.skills.items(), key=lambda kv: -kv[1].level) if v.level]
    asked = set((session.meta or {}).get("asked_quiz", []))
    q = None
    for sid in skill_ids:
        q = next((q for q in ctx.catalog.questions.values() if sid in q.skills and q.id not in asked and q.mode != "behavioral"), None)
        if q:
            break
    if not q:
        return {"text": "I've run out of fresh quiz questions for your current skills — try Interview mode for a longer session."}
    meta = dict(session.meta or {})
    meta["pending_quiz"] = q.id
    meta["asked_quiz"] = [*asked, q.id]
    session.meta = meta
    return {"text": f"**Quiz ({', '.join(ctx.catalog.skill_name(s) for s in q.skills)}):** {q.prompt}\n\nAnswer in your own words — I'll check which key concepts you covered."}


async def tool_quiz_answer(ctx: MentorContext, session: ChatSession, message: str) -> dict:
    meta = dict(session.meta or {})
    q = ctx.catalog.questions[meta.pop("pending_quiz")]
    session.meta = meta
    ev = await evaluate(q, message, ctx.career.name if ctx.career else "your target role")
    passed = ev["technical_coverage"] >= 60
    if passed:
        ctx.db.add(Progress(user_id=ctx.user.id, kind="quiz", ref_id=q.id, skill_ids=q.skills, title=f"Quiz: {q.prompt[:80]}",
                            detail=f"Covered {ev['technical_coverage']}% of key concepts"))
    lines = [f"**Concept coverage:** {ev['technical_coverage']}% ({ev['technical_coverage_label']}) · **Clarity:** {ev['clarity_label']}"]
    if ev["covered_concepts"]:
        lines.append("✓ " + "; ".join(ev["covered_concepts"]))
    if ev["missing_concepts"]:
        lines.append("Missing: " + "; ".join(ev["missing_concepts"]))
    lines.append(ev["feedback"])
    if passed:
        lines.append("_Saved as quiz evidence on your Progress page._")
    return {"text": "\n\n".join(lines), "action": {"type": "evidence_added"} if passed else None}


# ------------------------------------------------------------------------ orchestration
SYSTEM_PROMPT = """You are PathFinder's AI career mentor: warm, concise, practical and honest.
Principles:
- Use the user's profile and roadmap below. Treat it as what the USER told us; say "you mentioned"/"your profile" for it.
- Information from the knowledge base must be cited with [n] markers matching the numbered sources.
- Never claim a career is objectively best, never guarantee jobs, salaries or outcomes, never invent requirements.
- Prefer practical evidence (projects, deployed work) over collecting certificates.
- If a tool result is provided, build your answer around it and keep its facts exactly.
- Keep answers under ~180 words unless asked for depth. Use short paragraphs or bullets."""


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_text(text: str) -> AsyncIterator[str]:
    for i, part in enumerate(re.split(r"(\s+)", text)):
        if part:
            yield part
            if i % 6 == 0:
                await asyncio.sleep(0.012)


def get_session(db: Session, user: User, session_id: str | None) -> ChatSession:
    if session_id:
        s = db.get(ChatSession, session_id)
        if not s or s.user_id != user.id or s.kind != "mentor":
            raise NotFound("Conversation not found.")
        return s
    s = ChatSession(user_id=user.id, kind="mentor", title="Mentor conversation", meta={})
    db.add(s)
    db.flush()
    return s


async def chat_stream(db: Session, user: User, catalog: Catalog, message: str, session_id: str | None) -> AsyncIterator[str]:
    session = get_session(db, user, session_id)
    if session.title == "Mentor conversation":
        session.title = message[:60]
    history = [(m.role, m.content) for m in session.messages][-10:]
    db.add(ChatMessage(session_id=session.id, role="user", content=message))
    ctx = MentorContext(db, user, catalog)
    intent = detect_intent(message, bool((session.meta or {}).get("pending_quiz")))

    result: dict = {}
    try:
        if intent == "next_step":
            result = tool_next_step(ctx)
        elif intent == "explain":
            result = tool_explain(ctx, message)
        elif intent == "project":
            result = tool_project(ctx)
        elif intent == "review_project":
            result = tool_review_project(ctx, message)
        elif intent == "readiness":
            result = tool_readiness(ctx)
        elif intent == "adjust_hours":
            result = tool_adjust_hours(ctx, message)
        elif intent == "known_skill":
            result = tool_known(ctx, message)
        elif intent == "change_career":
            result = tool_change_career(ctx, message)
        elif intent == "quiz":
            result = tool_quiz(ctx, session)
        elif intent == "quiz_answer":
            result = await tool_quiz_answer(ctx, session, message)
    except AppError as exc:
        result = {"text": exc.message}

    # Retrieval (knowledge base) for grounding and citations.
    sources: list[dict] = []
    if intent in ("explain", "general", "next_step", "project"):
        try:
            hits = get_retriever().search(result.get("query") or message, k=4)
            sources = [{"n": i + 1, **{k: h[k] for k in ("id", "title", "type", "source", "url")}, "snippet": h["text"][:280]}
                       for i, h in enumerate(hits)]
        except AppError:
            sources = []

    action = result.get("action")
    yield _sse("meta", {"session_id": session.id, "intent": intent, "sources": sources, "action": action,
                        "ai": get_llm().available, "model": get_llm().model_name})

    llm = get_llm()
    full = ""
    deterministic = intent in ("adjust_hours", "known_skill", "change_career", "quiz", "quiz_answer")
    if llm.available and not deterministic:
        context = ctx.summary()
        src_block = "\n".join(f"[{s['n']}] {s['title']} ({s['source']}): {s['snippet']}" for s in sources) or "None"
        tool_block = result.get("text") or "None"
        prompt = f"USER PROFILE & ROADMAP:\n{context}\n\nTOOL RESULT:\n{tool_block}\n\nKNOWLEDGE BASE SOURCES:\n{src_block}\n\nUSER MESSAGE:\n{message}"
        try:
            async for tok in llm.stream(SYSTEM_PROMPT, history, prompt):
                full += tok
                yield _sse("token", {"t": tok})
        except AppError as exc:
            if not full:
                fallback = result.get("text") or _offline_general(sources, message)
                full = fallback + f"\n\n_({exc.message} Showing an offline answer.)_"
                async for tok in _stream_text(full):
                    yield _sse("token", {"t": tok})
        if full and not safe_text(full, 10000):
            full += "\n\n_Note: no one can guarantee specific job or salary outcomes._"
    else:
        full = result.get("text") or _offline_general(sources, message)
        async for tok in _stream_text(full):
            yield _sse("token", {"t": tok})

    db.add(ChatMessage(session_id=session.id, role="assistant", content=full, meta={"intent": intent, "sources": sources, "action": action}))
    db.commit()
    yield _sse("done", {"session_id": session.id})


def _offline_general(sources: list[dict], message: str) -> str:
    if not sources:
        return ("I can help with your next step, explaining a skill, project ideas, reviewing a project, quizzes, readiness, "
                "or adjusting your roadmap. Try one of the suggestions below.")
    top = sources[0]
    lines = [f"Here's what PathFinder's knowledge base says [{top['n']}]:", "", top["snippet"]]
    if len(sources) > 1:
        lines += ["", "Related: " + "; ".join(f"{s['title']} [{s['n']}]" for s in sources[1:3])]
    lines += ["", "_Connect an AI provider (OpenAI or Gemini) for fuller, conversational answers._"]
    return "\n".join(lines)


def list_sessions(db: Session, user: User) -> list[dict]:
    return [{"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()}
            for s in sorted((s for s in user.chat_sessions if s.kind == "mentor"), key=lambda s: s.created_at, reverse=True)[:20]]


def session_messages(db: Session, user: User, session_id: str) -> list[dict]:
    s = get_session(db, user, session_id)
    return [{"role": m.role, "content": m.content, "meta": m.meta or {}, "created_at": m.created_at.isoformat()} for m in s.messages]
