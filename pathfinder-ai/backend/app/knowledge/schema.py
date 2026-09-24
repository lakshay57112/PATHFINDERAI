"""Pydantic schemas that validate the YAML knowledge base at load time."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Importance = Literal["core", "important", "useful"]


class Resource(BaseModel):
    title: str
    provider: str | None = None
    url: str | None = None
    type: str = "docs"


class SkillDef(BaseModel):
    id: str
    name: str
    category: str
    domains: list[str] = Field(default_factory=list)
    onboarding: str | None = None
    aliases: list[str] = Field(default_factory=list)
    prereqs: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    hours: list[float] = Field(default_factory=lambda: [10, 30, 60])
    description: str = ""
    learn: list[Resource] = Field(default_factory=list)
    practice: str = ""
    build: str = ""
    prove: str = ""

    @field_validator("hours")
    @classmethod
    def _three_hours(cls, v: list[float]) -> list[float]:
        if len(v) != 3:
            raise ValueError("hours must have exactly 3 values")
        return v

    def hours_between(self, from_level: int, to_level: int) -> float:
        return float(sum(self.hours[lvl] for lvl in range(max(0, from_level), min(3, to_level))))


class CareerSkillReq(BaseModel):
    skill_id: str
    level: int = Field(ge=1, le=3)
    importance: Importance


class Phase(BaseModel):
    name: str
    skills: list[str]


class Signals(BaseModel):
    domains: dict[str, float] = Field(default_factory=dict)
    activities: list[str] = Field(default_factory=list)
    work_styles: list[str] = Field(default_factory=list)


class CareerDef(BaseModel):
    id: str
    name: str
    family: str
    categories: list[str]
    summary: str
    what_they_do: str
    responsibilities: list[str] = Field(default_factory=list)
    skills: list[CareerSkillReq]
    technologies: list[str] = Field(default_factory=list)
    entry_routes: list[str] = Field(default_factory=list)
    example_projects: list[str] = Field(default_factory=list)
    project_templates: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    who_might_enjoy: list[str] = Field(default_factory=list)
    questions_to_explore: list[str] = Field(default_factory=list)
    signals: Signals = Field(default_factory=Signals)
    skill_focus: str = ""
    typical_outputs: str = ""
    phases: list[Phase] = Field(default_factory=list)

    @field_validator("skills", mode="before")
    @classmethod
    def _parse_skills(cls, v):
        # YAML form: {skill_id: [level, importance]}
        if isinstance(v, dict):
            return [{"skill_id": k, "level": val[0], "importance": val[1]} for k, val in v.items()]
        return v

    def requirement(self, skill_id: str) -> CareerSkillReq | None:
        return next((s for s in self.skills if s.skill_id == skill_id), None)


class CertificateDef(BaseModel):
    id: str
    name: str
    provider: str
    type: Literal["exam", "course"]
    level: str
    skills: list[str]
    url: str | None = None
    aliases: list[str] = Field(default_factory=list)
    notes: str = ""


class ProjectTemplate(BaseModel):
    id: str
    name: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    hours: float
    skills: list[str]
    uses: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    problem: str
    architecture: list[str]
    technologies: list[str]
    expected_output: str
    portfolio_value: str
    flavors: dict[str, str] = Field(default_factory=dict)


class Concept(BaseModel):
    name: str
    keywords: list[str]


class InterviewQuestion(BaseModel):
    id: str
    mode: Literal["technical", "behavioral", "case_study", "system_design", "sql", "coding", "domain"]
    skills: list[str] = Field(default_factory=list)
    prompt: str
    concepts: list[Concept]
    follow_ups: list[str] = Field(default_factory=list)
