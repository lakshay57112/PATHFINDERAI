"""Request schemas for the public API. Responses are produced by the engines as plain dicts."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

from app.knowledge.vocab import ACTIVITIES, DOMAINS, EXPERIENCE_LEVELS, LEARNING_PREFERENCES, WORK_STYLES

SkillLevelLabel = Literal["beginner", "intermediate", "advanced", "unsure", "none"]


def _only(allowed, values: list[str], what: str) -> list[str]:
    bad = [v for v in values if v not in allowed]
    if bad:
        raise ValueError(f"Unknown {what}: {', '.join(bad)}")
    return list(dict.fromkeys(values))


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class SkillIn(BaseModel):
    skill_id: str
    level: SkillLevelLabel


class EducationIn(BaseModel):
    level: str | None = Field(default=None, max_length=60)
    degree: str | None = Field(default=None, max_length=120)
    field: str | None = Field(default=None, max_length=120)
    institution: str | None = Field(default=None, max_length=160)


class CertificateIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    issuer: str | None = Field(default=None, max_length=160)
    completed_on: date | None = None
    description: str | None = Field(default=None, max_length=4000)


class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=6000)
    technologies: list[str] = Field(default_factory=list, max_length=40)
    role: str | None = Field(default=None, max_length=120)
    github_url: HttpUrl | None = None
    demo_url: HttpUrl | None = None
    status: Literal["planned", "in_progress", "completed"] = "completed"


class InterestsIn(BaseModel):
    interests: list[str] = Field(max_length=15)

    @field_validator("interests")
    @classmethod
    def _v(cls, v):
        return _only(DOMAINS, v, "interest")


class SkillsIn(BaseModel):
    skills: list[SkillIn] = Field(max_length=120)


class OnboardingIn(BaseModel):
    interests: list[str] = Field(default_factory=list)
    skills: list[SkillIn] = Field(default_factory=list, max_length=120)
    activities: list[str] = Field(default_factory=list)
    work_styles: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list, max_length=20)
    education: EducationIn | None = None
    experience_level: str | None = None
    work_experience: str | None = Field(default=None, max_length=4000)
    internships: str | None = Field(default=None, max_length=4000)
    career_goals: str | None = Field(default=None, max_length=2000)
    learning_preferences: list[str] = Field(default_factory=list)
    hours_per_week: int = Field(default=8, ge=1, le=80)
    certificates: list[CertificateIn] = Field(default_factory=list, max_length=30)
    projects: list[ProjectIn] = Field(default_factory=list, max_length=30)

    @field_validator("interests")
    @classmethod
    def _interests(cls, v):
        return _only(DOMAINS, v, "interest")

    @field_validator("activities")
    @classmethod
    def _acts(cls, v):
        return _only(ACTIVITIES, v, "activity")

    @field_validator("work_styles")
    @classmethod
    def _styles(cls, v):
        return _only(WORK_STYLES, v, "work style")

    @field_validator("experience_level")
    @classmethod
    def _exp(cls, v):
        if v and v not in EXPERIENCE_LEVELS:
            raise ValueError("Unknown experience level")
        return v

    @field_validator("learning_preferences")
    @classmethod
    def _prefs(cls, v):
        return _only(LEARNING_PREFERENCES, v, "learning preference")


class ProfileUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    hours_per_week: int | None = Field(default=None, ge=1, le=80)
    career_goals: str | None = Field(default=None, max_length=2000)
    learning_preferences: list[str] | None = None
    activities: list[str] | None = None
    work_styles: list[str] | None = None


class DiscoverIn(BaseModel):
    limit: int = Field(default=6, ge=1, le=10)


class CompareIn(BaseModel):
    career_ids: list[str] = Field(min_length=2, max_length=4)


class SelectCareerIn(BaseModel):
    career_id: str


class RoadmapGenerateIn(BaseModel):
    career_id: str | None = None
    hours_per_week: int | None = Field(default=None, ge=1, le=80)


class StepUpdateIn(BaseModel):
    status: Literal["todo", "in_progress", "done", "skipped"]
    evidence_url: HttpUrl | None = None
    note: str | None = Field(default=None, max_length=1000)


class RoadmapAdjustIn(BaseModel):
    hours_per_week: int | None = Field(default=None, ge=1, le=80)
    known_skills: list[str] = Field(default_factory=list, max_length=30)


class RecommendationsIn(BaseModel):
    career_id: str | None = None


class MentorChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class InterviewStartIn(BaseModel):
    career_id: str | None = None
    mode: Literal["technical", "behavioral", "case_study", "system_design", "sql", "coding", "domain"] = "technical"


class InterviewAnswerIn(BaseModel):
    session_id: str
    answer: str = Field(min_length=1, max_length=8000)


class MarketAnalyzeIn(BaseModel):
    career_id: str
    country: str | None = None
    city: str | None = None
    remote: bool | None = None
    industry: str | None = None
    include_synthetic: bool = True


class PostingIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=20, max_length=20000)
    country: str | None = None
    city: str | None = None
    remote: bool = False
    industry: str | None = None
    posted_on: date | None = None


class MarketIngestIn(BaseModel):
    source: str = Field(min_length=2, max_length=160, description="Where these postings came from, e.g. 'LinkedIn search, Bengaluru, Sep 2026'")
    career_id: str | None = None
    postings: list[PostingIn] = Field(min_length=1, max_length=200)
