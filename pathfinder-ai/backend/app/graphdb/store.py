"""Career knowledge graph — Neo4j when configured, an in-memory graph otherwise.

Schema
  (:Career)-[:REQUIRES {level, importance}]->(:Skill)
  (:Skill)-[:PREREQUISITE_OF]->(:Skill)
  (:Skill)-[:RELATED_TO {weight}]->(:Skill)        # co-required by several careers
  (:Career)-[:USES]->(:Technology)
  (:Career)-[:BENEFITS_FROM]->(:Certificate)
  (:Career)-[:DEMONSTRATED_BY]->(:Project)
  (:Career)-[:RELATED_TO]->(:Career)
  (:Certificate)-[:COVERS]->(:Skill)
  (:Project)-[:BUILDS]->(:Skill)
"""
from __future__ import annotations

import logging
import re
import threading
from collections import Counter, defaultdict
from itertools import combinations

from app.core.config import get_settings
from app.knowledge.catalog import Catalog, get_catalog

log = logging.getLogger("pathfinder.graph")


def _tech_id(name: str) -> str:
    return "tech:" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def catalog_edges(catalog: Catalog) -> tuple[dict[str, dict], list[dict]]:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def node(nid, label, name, **props):
        nodes.setdefault(nid, {"id": nid, "label": label, "name": name, **props})

    for s in catalog.skills.values():
        node(f"skill:{s.id}", "Skill", s.name, category=s.category)
        for p in s.prereqs:
            edges.append({"source": f"skill:{p}", "target": f"skill:{s.id}", "type": "PREREQUISITE_OF"})
    co = Counter()
    for c in catalog.careers.values():
        node(f"career:{c.id}", "Career", c.name, family=c.family)
        core = sorted(r.skill_id for r in c.skills if r.importance != "useful")
        co.update(combinations(core, 2))
        for r in c.skills:
            edges.append({"source": f"career:{c.id}", "target": f"skill:{r.skill_id}", "type": "REQUIRES",
                          "level": r.level, "importance": r.importance})
        for t in c.technologies:
            node(_tech_id(t), "Technology", t)
            edges.append({"source": f"career:{c.id}", "target": _tech_id(t), "type": "USES"})
        for cid in c.certificates:
            edges.append({"source": f"career:{c.id}", "target": f"cert:{cid}", "type": "BENEFITS_FROM"})
        for pid in c.project_templates:
            edges.append({"source": f"career:{c.id}", "target": f"project:{pid}", "type": "DEMONSTRATED_BY"})
        for rid in c.related:
            edges.append({"source": f"career:{c.id}", "target": f"career:{rid}", "type": "RELATED_TO"})
    for (a, b), n in co.items():
        if n >= 3:
            edges.append({"source": f"skill:{a}", "target": f"skill:{b}", "type": "RELATED_TO", "weight": n})
    for cert in catalog.certificates.values():
        node(f"cert:{cert.id}", "Certificate", cert.name, provider=cert.provider)
        for sid in cert.skills:
            edges.append({"source": f"cert:{cert.id}", "target": f"skill:{sid}", "type": "COVERS"})
    for p in catalog.projects.values():
        node(f"project:{p.id}", "Project", p.name, difficulty=p.difficulty)
        for sid in p.skills:
            edges.append({"source": f"project:{p.id}", "target": f"skill:{sid}", "type": "BUILDS"})
    return nodes, edges


class MemoryGraph:
    backend = "memory"

    def __init__(self, catalog: Catalog) -> None:
        self.nodes, self.edges = catalog_edges(catalog)
        self.out = defaultdict(list)
        self.inc = defaultdict(list)
        for e in self.edges:
            self.out[e["source"]].append(e)
            self.inc[e["target"]].append(e)

    def career_subgraph(self, career_id: str, *, max_tech: int = 6) -> dict:
        root = f"career:{career_id}"
        if root not in self.nodes:
            return {"nodes": [], "edges": []}
        keep = {root}
        edges = []
        techs = 0
        for e in self.out[root]:
            if e["type"] == "USES":
                techs += 1
                if techs > max_tech:
                    continue
            if e["type"] == "REQUIRES" and e.get("importance") == "useful":
                continue
            keep.add(e["target"])
            edges.append(e)
        return {"nodes": [self.nodes[n] for n in keep if n in self.nodes], "edges": edges}

    def related_careers(self, career_id: str) -> list[str]:
        return [e["target"].split(":", 1)[1] for e in self.out[f"career:{career_id}"] if e["type"] == "RELATED_TO"]

    def related_skills(self, skill_id: str, limit: int = 6) -> list[dict]:
        nid = f"skill:{skill_id}"
        rel = [(e["target"], e.get("weight", 1), e["type"]) for e in self.out[nid] if e["type"] in ("RELATED_TO", "PREREQUISITE_OF")]
        rel += [(e["source"], e.get("weight", 1), e["type"]) for e in self.inc[nid] if e["type"] in ("RELATED_TO", "PREREQUISITE_OF")]
        rel.sort(key=lambda t: -t[1])
        seen, out = set(), []
        for n, w, t in rel:
            if n not in seen and n in self.nodes:
                seen.add(n)
                out.append({"skill_id": n.split(":", 1)[1], "name": self.nodes[n]["name"], "relation": t, "weight": w})
        return out[:limit]

    def careers_requiring(self, skill_id: str) -> list[str]:
        return [e["source"].split(":", 1)[1] for e in self.inc[f"skill:{skill_id}"] if e["type"] == "REQUIRES"]


class Neo4jGraph(MemoryGraph):  # pragma: no cover - requires a running Neo4j
    """Writes the same graph to Neo4j and answers queries with Cypher."""

    backend = "neo4j"

    def __init__(self, catalog: Catalog, driver) -> None:
        super().__init__(catalog)
        self.driver = driver
        self._sync()

    def _sync(self) -> None:
        by_label = defaultdict(list)
        for n in self.nodes.values():
            by_label[n["label"]].append(n)
        with self.driver.session() as s:
            for label in by_label:
                s.run(f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE")
            for label, items in by_label.items():
                s.run(f"UNWIND $rows AS r MERGE (n:{label} {{id: r.id}}) SET n += r", rows=items)
            by_type = defaultdict(list)
            for e in self.edges:
                by_type[e["type"]].append(e)
            for etype, items in by_type.items():
                s.run(
                    f"UNWIND $rows AS r MATCH (a {{id: r.source}}), (b {{id: r.target}}) MERGE (a)-[x:{etype}]->(b) "
                    f"SET x.level = r.level, x.importance = r.importance, x.weight = r.weight",
                    rows=items,
                )
        log.info("Neo4j graph synced: %d nodes, %d edges", len(self.nodes), len(self.edges))

    def career_subgraph(self, career_id: str, *, max_tech: int = 6) -> dict:
        q = (
            "MATCH (c:Career {id: $cid})-[r]->(n) "
            "WHERE NOT (type(r) = 'REQUIRES' AND r.importance = 'useful') "
            "RETURN c, r, n, type(r) AS t"
        )
        nodes, edges, techs = {}, [], 0
        with self.driver.session() as s:
            for rec in s.run(q, cid=f"career:{career_id}"):
                c, n, t = dict(rec["c"]), dict(rec["n"]), rec["t"]
                if t == "USES":
                    techs += 1
                    if techs > max_tech:
                        continue
                nodes[c["id"]] = c
                nodes[n["id"]] = n
                rel = dict(rec["r"])
                edges.append({"source": c["id"], "target": n["id"], "type": t, **{k: v for k, v in rel.items() if v is not None}})
        return {"nodes": list(nodes.values()), "edges": edges}

    def related_careers(self, career_id: str) -> list[str]:
        with self.driver.session() as s:
            res = s.run("MATCH (:Career {id: $cid})-[:RELATED_TO]->(o:Career) RETURN o.id AS id", cid=f"career:{career_id}")
            return [r["id"].split(":", 1)[1] for r in res]


_graph = None
_lock = threading.Lock()


def get_graph() -> MemoryGraph:
    global _graph
    with _lock:
        if _graph is None:
            catalog = get_catalog()
            s = get_settings()
            if s.neo4j_uri:
                try:
                    from neo4j import GraphDatabase

                    driver = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password), connection_timeout=3)
                    driver.verify_connectivity()
                    _graph = Neo4jGraph(catalog, driver)
                except Exception as exc:
                    log.warning("Neo4j unavailable (%s); using in-memory knowledge graph", exc)
            if _graph is None:
                _graph = MemoryGraph(catalog)
    return _graph
