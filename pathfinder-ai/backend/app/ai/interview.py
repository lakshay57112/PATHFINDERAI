"""Interview answer evaluation — LLM rubric when available, transparent offline rubric otherwise."""
from __future__ import annotations

import re

from app.ai.guards import safe_text
from app.ai.llm import try_structured
from app.ai.schemas import InterviewEvaluationAI
from app.knowledge.schema import InterviewQuestion

STRUCTURE_WORDS = ["first", "second", "then", "next", "finally", "because", "therefore", "for example", "e.g.", "such as", "trade-off", "tradeoff", "however"]


def _label(score: int) -> str:
    return "Strong" if score >= 75 else "Solid" if score >= 55 else "Partial" if score >= 30 else "Limited"


def evaluate_offline(q: InterviewQuestion, answer: str) -> dict:
    low = f" {answer.lower()} "
    covered, missing = [], []
    for c in q.concepts:
        (covered if any(k.lower() in low for k in c.keywords) else missing).append(c.name)
    coverage = round(100 * len(covered) / max(len(q.concepts), 1))
    words = len(re.findall(r"\w+", answer))
    sentences = max(1, len(re.findall(r"[.!?](\s|$)", answer)))
    structure_hits = sum(1 for w in STRUCTURE_WORDS if w in low)
    clarity = 35
    clarity += 25 if 60 <= words <= 350 else 12 if 30 <= words < 60 or 350 < words <= 600 else 0
    clarity += min(structure_hits, 4) * 7
    clarity += 12 if 12 <= words / sentences <= 28 else 4
    clarity = max(5, min(100, clarity))
    feedback = []
    if covered:
        feedback.append(f"You covered {', '.join(covered[:3]).lower()}.")
    if missing:
        feedback.append(f"A stronger answer would also address {', '.join(missing[:3]).lower()}.")
    if words < 40:
        feedback.append("Your answer is quite brief — walk through your reasoning step by step.")
    if structure_hits == 0 and words >= 40:
        feedback.append("Add structure (e.g. 'first… then… finally') and one concrete example.")
    return {
        "technical_coverage": coverage,
        "technical_coverage_label": _label(coverage),
        "accuracy": "not_assessed",
        "accuracy_notes": "Accuracy needs an AI provider to judge. Offline mode checks concept coverage and structure only.",
        "clarity": clarity,
        "clarity_label": _label(clarity),
        "covered_concepts": covered,
        "missing_concepts": missing,
        "feedback": " ".join(feedback) or "Good start — add depth and a concrete example.",
        "method": "offline_rubric",
    }


async def evaluate(q: InterviewQuestion, answer: str, career_name: str) -> dict:
    offline = evaluate_offline(q, answer)
    ai = await try_structured(
        "You are a fair, encouraging interviewer. Evaluate the candidate's answer against the listed concepts. "
        "Judge technical accuracy carefully; do not invent facts about the candidate. Keep feedback specific and kind.",
        f"Role: {career_name}\nQuestion: {q.prompt}\nConcepts a strong answer covers: {'; '.join(c.name for c in q.concepts)}\n"
        f"Candidate answer:\n{answer}\n\nReturn scores 0-100, concepts covered/missing (use the concept names given), "
        "feedback, and one natural follow-up question probing the weakest area.",
        InterviewEvaluationAI,
    )
    if not ai:
        return offline
    names = {c.name for c in q.concepts}
    return {
        "technical_coverage": ai.technical_coverage,
        "technical_coverage_label": _label(ai.technical_coverage),
        "accuracy": ai.accuracy,
        "accuracy_notes": safe_text(ai.accuracy_notes, 400) or "",
        "clarity": ai.clarity,
        "clarity_label": _label(ai.clarity),
        "covered_concepts": [c for c in ai.covered_concepts if c in names] or offline["covered_concepts"],
        "missing_concepts": [c for c in ai.missing_concepts if c in names] or offline["missing_concepts"],
        "feedback": safe_text(ai.feedback, 700) or offline["feedback"],
        "ai_follow_up": safe_text(ai.follow_up_question, 300),
        "method": "llm_rubric",
    }
