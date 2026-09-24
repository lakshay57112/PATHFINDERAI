"""Validation of AI-generated data before it's shown or persisted.

The LLM may *select* and *explain*, but anything referencing the knowledge base
(skills, careers) must resolve to real IDs, and free text is length-bounded and
screened for claims the product must never make (guaranteed jobs/salaries).
"""
from __future__ import annotations

import re

from app.knowledge.catalog import Catalog
from app.knowledge.vocab import DOMAINS

FORBIDDEN_CLAIMS = re.compile(
    r"\b(guarantee[sd]?|guaranteed (job|salary|offer|employment)|100% (job|placement)|you will (definitely )?get (a|the) job|"
    r"best career for you|scientifically (proven|determined))\b",
    re.I,
)


def valid_skill_ids(ids: list[str], catalog: Catalog) -> list[str]:
    return [s for s in dict.fromkeys(ids) if s in catalog.skills]


def valid_domains(ids: list[str]) -> list[str]:
    return [d for d in dict.fromkeys(ids) if d in DOMAINS]


def safe_text(text: str, max_len: int = 800) -> str | None:
    """Return text if it passes policy checks, else None (caller falls back to deterministic copy)."""
    if not text:
        return None
    text = text.strip()[:max_len]
    if FORBIDDEN_CLAIMS.search(text):
        return None
    return text


def hallucinated_skill_mentions(text: str, allowed_skill_ids: set[str], catalog: Catalog) -> list[str]:
    """Skills the text mentions that are outside the allowed set (used by evaluations)."""
    return [s for s in catalog.extract_skills(text) if s not in allowed_skill_ids]
