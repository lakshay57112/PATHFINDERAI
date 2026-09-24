"""A plain, DB-independent view of a user's profile that every engine consumes.

Keeping the engines pure (snapshot in → result out) makes them deterministic,
unit-testable and safe: the LLM layer can only enrich their outputs, never replace them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.knowledge.catalog import Catalog

EVIDENCE_RANK = {"stated": 0, "certificate": 1, "project": 2, "roadmap": 2, "assessment": 3}


@dataclass
class Evidence:
    kind: str  # stated | certificate | project | roadmap | assessment
    title: str
    ref_id: str | None = None

    def as_dict(self) -> dict:
        return {"kind": self.kind, "title": self.title, "ref_id": self.ref_id}


@dataclass
class SkillState:
    skill_id: str
    stated_level: int = 0
    unsure: bool = False
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def inferred_level(self) -> int:
        """Minimum level implied by non-stated evidence."""
        lvl = 0
        for ev in self.evidence:
            if ev.kind in ("project", "roadmap", "assessment"):
                lvl = max(lvl, 1)
            elif ev.kind == "certificate":
                lvl = max(lvl, 1)
        return lvl

    @property
    def level(self) -> int:
        return max(self.stated_level, self.inferred_level)

    @property
    def evidence_strength(self) -> str:
        kinds = [e.kind for e in self.evidence]
        if not kinds:
            return "stated" if self.stated_level else "none"
        return max(kinds, key=lambda k: EVIDENCE_RANK.get(k, 0))


@dataclass
class ProfileSnapshot:
    user_id: str
    name: str = ""
    interests: list[str] = field(default_factory=list)
    activities: list[str] = field(default_factory=list)
    work_styles: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    skills: dict[str, SkillState] = field(default_factory=dict)
    education: dict = field(default_factory=dict)
    experience_level: str | None = None
    career_goals: str | None = None
    learning_preferences: list[str] = field(default_factory=list)
    hours_per_week: int = 8
    certificates: list[dict] = field(default_factory=list)  # {id, name, catalog_id, skills}
    projects: list[dict] = field(default_factory=list)  # {id, name, skills, status, source, difficulty, domains}
    target_career_id: str | None = None

    def level(self, skill_id: str) -> int:
        s = self.skills.get(skill_id)
        return s.level if s else 0

    def state(self, skill_id: str) -> SkillState:
        return self.skills.get(skill_id) or SkillState(skill_id)

    def known_skill_ids(self, min_level: int = 1) -> list[str]:
        return [sid for sid, s in self.skills.items() if s.level >= min_level]


def attach_evidence(snapshot: ProfileSnapshot, catalog: Catalog) -> ProfileSnapshot:
    """Link projects and certificates to the skills they demonstrate."""
    for proj in snapshot.projects:
        if proj.get("status") not in (None, "completed"):
            continue
        for sid in proj.get("skills", []):
            if sid not in catalog.skills:
                continue
            st = snapshot.skills.setdefault(sid, SkillState(sid))
            st.evidence.append(Evidence("project", proj.get("name", "Project"), proj.get("id")))
    for cert in snapshot.certificates:
        for sid in cert.get("skills", []):
            if sid not in catalog.skills:
                continue
            st = snapshot.skills.setdefault(sid, SkillState(sid))
            st.evidence.append(Evidence("certificate", cert.get("name", "Certificate"), cert.get("id")))
    return snapshot
