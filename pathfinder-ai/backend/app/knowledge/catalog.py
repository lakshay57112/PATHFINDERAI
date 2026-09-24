"""Loads and validates the YAML knowledge base.

Adding a career is a data change: drop a new entry into ``data/careers/*.yaml`` and restart.
Referential integrity (skills, related careers, certificates, project templates) is checked
here so broken references fail loudly at startup rather than producing bad recommendations.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from app.core.config import get_settings
from app.knowledge.schema import CareerDef, CertificateDef, InterviewQuestion, ProjectTemplate, SkillDef
from app.knowledge.vocab import ACTIVITIES, DOMAINS, WORK_STYLES

log = logging.getLogger("pathfinder.catalog")


class CatalogError(ValueError):
    pass


@dataclass
class Catalog:
    skills: dict[str, SkillDef]
    careers: dict[str, CareerDef]
    certificates: dict[str, CertificateDef]
    projects: dict[str, ProjectTemplate]
    questions: dict[str, InterviewQuestion]
    _alias_patterns: list[tuple[re.Pattern, str]] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------ lookups
    def skill(self, skill_id: str) -> SkillDef:
        return self.skills[skill_id]

    def career(self, career_id: str) -> CareerDef:
        return self.careers[career_id]

    def skill_name(self, skill_id: str) -> str:
        s = self.skills.get(skill_id)
        return s.name if s else skill_id

    def career_hash(self, career_id: str) -> str:
        raw = json.dumps(self.careers[career_id].model_dump(), sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def careers_by_category(self) -> dict[str, list[CareerDef]]:
        out: dict[str, list[CareerDef]] = {}
        for c in self.careers.values():
            for cat in c.categories:
                out.setdefault(cat, []).append(c)
        return out

    # ---------------------------------------------------------- text extraction
    def extract_skills(self, text: str) -> list[str]:
        """Find taxonomy skills mentioned in free text via names and aliases (word-boundary match)."""
        if not text:
            return []
        lowered = f" {text.lower()} "
        found: list[str] = []
        for pattern, skill_id in self._alias_patterns:
            if skill_id not in found and pattern.search(lowered):
                found.append(skill_id)
        return found

    def build_alias_index(self) -> None:
        pairs: list[tuple[str, str]] = []
        for s in self.skills.values():
            terms = {s.name.lower(), s.id.replace("_", " ")} | {a.lower() for a in s.aliases}
            # Very short/ambiguous single-letter tokens (e.g. "r", "go") need stricter matching.
            for t in terms:
                pairs.append((t, s.id))
        # Longest terms first so "machine learning" wins over "learning"-like fragments.
        pairs.sort(key=lambda p: -len(p[0]))
        patterns = []
        for term, sid in pairs:
            if term in {"r", "go"}:
                # Ambiguous English words only count when written as a list item: "Python, R, SQL".
                pat = re.compile(rf"(?:^\s*|[,;/|(\[]\s*){re.escape(term)}(?=\s*(?:[,;/|)\]]|$))")
            else:
                pat = re.compile(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])")
            patterns.append((pat, sid))
        self._alias_patterns = patterns

    def match_certificate(self, name: str, issuer: str | None = None) -> CertificateDef | None:
        """Fuzzy-match a user-entered certificate name to the catalog."""
        from difflib import SequenceMatcher

        text = f"{name} {issuer or ''}".lower()
        best, best_score = None, 0.0
        for cert in self.certificates.values():
            candidates = [cert.name.lower(), *[a.lower() for a in cert.aliases]]
            for cand in candidates:
                if re.search(rf"(?<![a-z0-9]){re.escape(cand)}(?![a-z0-9])", text):
                    score = 0.9 + len(cand) / 1000
                else:
                    score = SequenceMatcher(None, name.lower(), cand).ratio()
                if score > best_score:
                    best, best_score = cert, score
        return best if best_score >= 0.72 else None


def _load_yaml_list(path: Path, *, all_strings: bool = False) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        # all_strings: treat every scalar as text (keyword lists contain words like "null"/"on").
        data = (yaml.load(fh, Loader=yaml.BaseLoader) if all_strings else yaml.safe_load(fh)) or []
    if not isinstance(data, list):
        raise CatalogError(f"{path.name}: expected a list of entries")
    return data


def _index(items, kind: str) -> dict:
    out = {}
    for item in items:
        if item.id in out:
            raise CatalogError(f"duplicate {kind} id: {item.id}")
        out[item.id] = item
    return out


def load_catalog(data_dir: Path | None = None) -> Catalog:
    data_dir = data_dir or get_settings().data_dir
    skills = _index([SkillDef(**d) for d in _load_yaml_list(data_dir / "skills.yaml")], "skill")
    careers_raw: list[dict] = []
    for path in sorted((data_dir / "careers").glob("*.yaml")):
        careers_raw.extend(_load_yaml_list(path))
    careers = _index([CareerDef(**d) for d in careers_raw], "career")
    certificates = _index([CertificateDef(**d) for d in _load_yaml_list(data_dir / "certificates.yaml")], "certificate")
    projects = _index([ProjectTemplate(**d) for d in _load_yaml_list(data_dir / "projects.yaml")], "project")
    questions = _index([InterviewQuestion(**d) for d in _load_yaml_list(data_dir / "interview.yaml", all_strings=True)], "question")

    cat = Catalog(skills, careers, certificates, projects, questions)
    _validate(cat)
    cat.build_alias_index()
    log.info("catalog loaded: %d careers, %d skills, %d certificates, %d projects, %d questions",
             len(careers), len(skills), len(certificates), len(projects), len(questions))
    return cat


def _validate(cat: Catalog) -> None:
    errors: list[str] = []

    def need(cond: bool, msg: str):
        if not cond:
            errors.append(msg)

    for s in cat.skills.values():
        for ref in s.prereqs + s.related:
            need(ref in cat.skills, f"skill {s.id}: unknown skill reference '{ref}'")
        for d in s.domains:
            need(d in DOMAINS, f"skill {s.id}: unknown domain '{d}'")
    for c in cat.careers.values():
        for req in c.skills:
            need(req.skill_id in cat.skills, f"career {c.id}: unknown skill '{req.skill_id}'")
        for ref in c.related:
            need(ref in cat.careers, f"career {c.id}: unknown related career '{ref}'")
        for ref in c.certificates:
            need(ref in cat.certificates, f"career {c.id}: unknown certificate '{ref}'")
        for ref in c.project_templates:
            need(ref in cat.projects, f"career {c.id}: unknown project template '{ref}'")
        for d in list(c.signals.domains) + c.categories:
            need(d in DOMAINS, f"career {c.id}: unknown domain '{d}'")
        for a in c.signals.activities:
            need(a in ACTIVITIES, f"career {c.id}: unknown activity '{a}'")
        for w in c.signals.work_styles:
            need(w in WORK_STYLES, f"career {c.id}: unknown work style '{w}'")
        for ph in c.phases:
            for sid in ph.skills:
                need(c.requirement(sid) is not None, f"career {c.id}: phase skill '{sid}' is not a requirement")
    for cert in cat.certificates.values():
        for sid in cert.skills:
            need(sid in cat.skills, f"certificate {cert.id}: unknown skill '{sid}'")
    for p in cat.projects.values():
        for sid in p.skills + p.uses:
            need(sid in cat.skills, f"project {p.id}: unknown skill '{sid}'")
    for q in cat.questions.values():
        for sid in q.skills:
            need(sid in cat.skills, f"question {q.id}: unknown skill '{sid}'")
    if errors:
        raise CatalogError("Knowledge base integrity errors:\n  - " + "\n  - ".join(errors))


@lru_cache
def get_catalog() -> Catalog:
    return load_catalog()
