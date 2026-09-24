"""Builds the RAG knowledge base from the curated catalog.

Every chunk carries a citation (title, type, source label and URL where one exists) so
answers can distinguish PathFinder's knowledge base from the user's own data.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.knowledge.catalog import Catalog
from app.knowledge.vocab import LEVELS


@dataclass
class KBDocument:
    id: str
    type: str  # career | skill | resource | certificate | project | interview | market
    title: str
    text: str
    metadata: dict = field(default_factory=dict)

    def citation(self) -> dict:
        return {"id": self.id, "type": self.type, "title": self.title, "url": self.metadata.get("url"),
                "source": self.metadata.get("source", "PathFinder career knowledge base")}


def build_documents(catalog: Catalog) -> list[KBDocument]:
    docs: list[KBDocument] = []
    for c in catalog.careers.values():
        core = ", ".join(f"{catalog.skill_name(r.skill_id)} ({LEVELS[r.level].lower()})" for r in c.skills if r.importance == "core")
        other = ", ".join(catalog.skill_name(r.skill_id) for r in c.skills if r.importance != "core")
        docs.append(KBDocument(f"career:{c.id}:overview", "career", f"{c.name} — overview",
                               f"{c.name}. {c.summary} {c.what_they_do} Typical outputs: {c.typical_outputs}. "
                               f"Who might enjoy it: {'; '.join(c.who_might_enjoy)}.",
                               {"career_id": c.id}))
        docs.append(KBDocument(f"career:{c.id}:skills", "career", f"{c.name} — skills and technologies",
                               f"Core skills for a {c.name}: {core}. Other useful skills: {other}. "
                               f"Common technologies: {', '.join(c.technologies)}. Responsibilities: {'; '.join(c.responsibilities)}.",
                               {"career_id": c.id}))
        docs.append(KBDocument(f"career:{c.id}:entry", "career", f"{c.name} — entry routes and questions",
                               f"Common entry routes into {c.name} roles: {'; '.join(c.entry_routes)}. Example projects: "
                               f"{'; '.join(c.example_projects)}. Questions to explore before choosing it: {'; '.join(c.questions_to_explore)}",
                               {"career_id": c.id}))
    for s in catalog.skills.values():
        docs.append(KBDocument(f"skill:{s.id}", "skill", f"{s.name} — what it is and how to learn it",
                               f"{s.name}: {s.description} Also known as: {', '.join(s.aliases[:6])}. Practice: {s.practice} "
                               f"Build: {s.build} Prove it: {s.prove}",
                               {"skill_id": s.id}))
        for i, r in enumerate(s.learn):
            docs.append(KBDocument(f"resource:{s.id}:{i}", "resource", f"{r.title} ({r.provider})",
                                   f"Learning resource for {s.name}: {r.title} by {r.provider}. Type: {r.type}.",
                                   {"skill_id": s.id, "url": r.url, "source": r.provider or "Resource metadata"}))
    for cert in catalog.certificates.values():
        docs.append(KBDocument(f"certificate:{cert.id}", "certificate", cert.name,
                               f"{cert.name} from {cert.provider}. {cert.type.title()}, {cert.level} level. Covers "
                               f"{', '.join(catalog.skill_name(x) for x in cert.skills)}. {cert.notes}",
                               {"url": cert.url, "source": f"Certificate metadata ({cert.provider})"}))
    for p in catalog.projects.values():
        docs.append(KBDocument(f"project:{p.id}", "project", f"Project template: {p.name}",
                               f"{p.name} ({p.difficulty}, ~{p.hours:.0f}h). Problem: {p.problem} Architecture: "
                               f"{' → '.join(p.architecture)}. Technologies: {', '.join(p.technologies)}. Skills: "
                               f"{', '.join(catalog.skill_name(x) for x in p.skills)}. Output: {p.expected_output}",
                               {"project_id": p.id}))
    for q in catalog.questions.values():
        docs.append(KBDocument(f"interview:{q.id}", "interview", f"Interview topic: {q.prompt[:80]}",
                               f"Interview question ({q.mode}): {q.prompt} A strong answer covers: {'; '.join(c.name for c in q.concepts)}.",
                               {"question_id": q.id}))
    return docs
