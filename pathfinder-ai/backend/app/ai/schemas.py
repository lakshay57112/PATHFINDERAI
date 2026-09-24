"""Structured outputs requested from the LLM. All are validated again by ``guards`` before use."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CareerNarrative(BaseModel):
    career_id: str = Field(description="Must be one of the provided career ids")
    explanation: str = Field(max_length=420, description="2 sentences on why this path may fit, referring only to the user's stated profile")


class DiscoveryNarrative(BaseModel):
    intro: str = Field(max_length=300)
    careers: list[CareerNarrative] = Field(max_length=10)


class ProjectAnalysisAI(BaseModel):
    skill_ids: list[str] = Field(description="Skill ids from the provided taxonomy only", max_length=20)
    difficulty: Literal["beginner", "intermediate", "advanced"]
    domains: list[str] = Field(max_length=3)
    summary: str = Field(max_length=300)


class CertificateAnalysisAI(BaseModel):
    skill_ids: list[str] = Field(max_length=20)
    topics: list[str] = Field(max_length=12)
    level: Literal["foundational", "intermediate", "associate", "professional"]
    provider: str | None = None


class InterviewEvaluationAI(BaseModel):
    technical_coverage: int = Field(ge=0, le=100)
    accuracy: Literal["accurate", "mostly_accurate", "contains_errors", "unclear"]
    accuracy_notes: str = Field(max_length=400)
    clarity: int = Field(ge=0, le=100)
    covered_concepts: list[str] = Field(max_length=10)
    missing_concepts: list[str] = Field(max_length=10)
    feedback: str = Field(max_length=700)
    follow_up_question: str = Field(max_length=300)
