"""
Skill Orchestrator — core business logic.

Depends only on the abstract interfaces (EmbeddingProvider, SkillRepository)
so the underlying model and database can be swapped freely.
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.interfaces import EmbeddingProvider, SkillRepository
from app.core.models import SkillCreate, SkillDiscovery, SkillRead, SkillTree

logger = logging.getLogger(__name__)


class SkillOrchestrator:
    """Search-then-Traverse orchestrator."""

    def __init__(self, embedding: EmbeddingProvider, repository: SkillRepository):
        self._embedding = embedding
        self._repo = repository

    # ── Discovery ─────────────────────────────────────────────

    def discover(self, query: str, k: int = 3) -> list[SkillDiscovery]:
        """Vector-search for skills matching a natural-language query."""
        vector = self._embedding.encode(query)
        hits = self._repo.search_by_vector(vector, k=k)
        return [
            SkillDiscovery(
                skill_id=h["skill_id"],
                summary=h.get("summary", ""),
                sub_skills=h.get("sub_skills", []),
                score=h.get("score", 0.0),
            )
            for h in hits
        ]

    # ── Navigation / Targeted Fetch ───────────────────────────

    def get_skill(self, skill_id: str, include_instruction: bool = True) -> SkillRead | None:
        """Fetch a single skill by ID."""
        fields = ["skill_id", "summary", "is_folder", "sub_skills"]
        if include_instruction:
            fields.append("instruction")
        doc = self._repo.get_by_id(skill_id, fields=fields)
        if doc is None:
            return None
        return SkillRead(**doc)

    def get_sub_skills(self, skill_id: str) -> list[SkillDiscovery]:
        """Load lightweight info for every child of *skill_id*."""
        parent = self._repo.get_by_id(skill_id, fields=["sub_skills"])
        if not parent:
            return []
        results: list[SkillDiscovery] = []
        for sid in parent.get("sub_skills", []):
            child = self._repo.get_by_id(sid, fields=["skill_id", "summary", "sub_skills"])
            if child:
                results.append(
                    SkillDiscovery(
                        skill_id=child["skill_id"],
                        summary=child.get("summary", ""),
                        sub_skills=child.get("sub_skills", []),
                    )
                )
        return results

    # ── Recursive Traversal ───────────────────────────────────

    def resolve(self, query: str) -> dict[str, Any]:
        """
        Full agentic resolution loop:
        1. Discover the best entry-point skill.
        2. If it is a folder, list its children.
        3. Return the context needed by the LLM.
        """
        discoveries = self.discover(query, k=1)
        if not discoveries:
            return {"resolved": False, "message": "No matching skill found."}

        entry = discoveries[0]
        skill = self.get_skill(entry.skill_id)
        if skill is None:
            return {"resolved": False, "message": "Skill disappeared after discovery."}

        if skill.is_folder and skill.sub_skills:
            children = self.get_sub_skills(skill.skill_id)
            return {
                "resolved": True,
                "entry": skill.model_dump(),
                "children": [c.model_dump() for c in children],
                "hint": "Pick a sub-skill and call get_skill to load its instruction.",
            }

        return {"resolved": True, "skill": skill.model_dump()}

    # ── CRUD ──────────────────────────────────────────────────

    def create_or_update_skill(self, payload: SkillCreate) -> SkillRead:
        """Create or update a skill, auto-generating the embedding vector."""
        vector = self._embedding.encode(payload.summary)
        doc = payload.model_dump()
        doc["skill_desc_vector"] = vector
        self._repo.upsert(doc)
        logger.info("Upserted skill: %s", payload.skill_id)
        return SkillRead(**payload.model_dump())

    def delete_skill(self, skill_id: str) -> bool:
        return self._repo.delete(skill_id)

    def list_skills(self) -> list[SkillDiscovery]:
        docs = self._repo.list_all()
        return [
            SkillDiscovery(
                skill_id=d["skill_id"],
                summary=d.get("summary", ""),
                sub_skills=d.get("sub_skills", []),
            )
            for d in docs
        ]

    # ── Tree Builder (for dashboard visualization) ────────────

    def build_tree(self) -> list[SkillTree]:
        """Build a forest of SkillTree nodes from the flat index."""
        all_docs = self._repo.list_all(size=500)
        lookup: dict[str, dict] = {d["skill_id"]: d for d in all_docs}
        child_ids: set[str] = set()
        for d in all_docs:
            child_ids.update(d.get("sub_skills", []))

        roots = [d for d in all_docs if d["skill_id"] not in child_ids]

        def _build(doc: dict) -> SkillTree:
            children = []
            for sid in doc.get("sub_skills", []):
                child = lookup.get(sid)
                if child:
                    children.append(_build(child))
            return SkillTree(
                skill_id=doc["skill_id"],
                summary=doc.get("summary", ""),
                is_folder=doc.get("is_folder", False),
                children=children,
            )

        return [_build(r) for r in roots]

    # ── Health ────────────────────────────────────────────────

    def health(self) -> dict:
        es_ok = self._repo.health_check()
        return {
            "elasticsearch": "ok" if es_ok else "unreachable",
            "embedding_model": "loaded",
            "embedding_dims": self._embedding.get_dimensions(),
        }
