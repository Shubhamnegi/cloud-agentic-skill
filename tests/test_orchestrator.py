"""
Unit tests for the SkillOrchestrator — runs entirely in-memory.
"""
from __future__ import annotations

import pytest

from app.core.models import SkillCreate
from app.services.orchestrator import SkillOrchestrator
from tests.fakes import FakeEmbeddingProvider, FakeSkillRepository


@pytest.fixture
def orchestrator() -> SkillOrchestrator:
    return SkillOrchestrator(
        embedding=FakeEmbeddingProvider(dims=4),
        repository=FakeSkillRepository(),
    )


def _seed(orch: SkillOrchestrator):
    """Insert a small skill tree."""
    orch.create_or_update_skill(SkillCreate(
        skill_id="SQL_SKILL",
        summary="SQL database skills",
        is_folder=True,
        sub_skills=["SQL_MIGRATION", "SQL_OPT"],
        instruction="Top-level SQL.",
    ))
    orch.create_or_update_skill(SkillCreate(
        skill_id="SQL_MIGRATION",
        summary="DB migration and sharding",
        is_folder=False,
        sub_skills=[],
        instruction="# Migration Guide\nDetailed content here.",
    ))
    orch.create_or_update_skill(SkillCreate(
        skill_id="SQL_OPT",
        summary="Query optimization",
        is_folder=False,
        sub_skills=[],
        instruction="# Optimization\nIndex tuning…",
    ))


class TestCRUD:
    def test_create_and_get(self, orchestrator: SkillOrchestrator):
        _seed(orchestrator)
        skill = orchestrator.get_skill("SQL_SKILL")
        assert skill is not None
        assert skill.skill_id == "SQL_SKILL"
        assert skill.is_folder is True

    def test_list_skills(self, orchestrator: SkillOrchestrator):
        _seed(orchestrator)
        skills = orchestrator.list_skills()
        assert len(skills) == 3

    def test_delete(self, orchestrator: SkillOrchestrator):
        _seed(orchestrator)
        assert orchestrator.delete_skill("SQL_OPT") is True
        assert orchestrator.get_skill("SQL_OPT") is None
        assert orchestrator.delete_skill("NONEXISTENT") is False


class TestDiscovery:
    def test_discover_returns_results(self, orchestrator: SkillOrchestrator):
        _seed(orchestrator)
        results = orchestrator.discover("sharding database", k=2)
        assert len(results) <= 2
        assert all(r.skill_id for r in results)

    def test_get_sub_skills(self, orchestrator: SkillOrchestrator):
        _seed(orchestrator)
        children = orchestrator.get_sub_skills("SQL_SKILL")
        ids = {c.skill_id for c in children}
        assert "SQL_MIGRATION" in ids
        assert "SQL_OPT" in ids


class TestTree:
    def test_build_tree(self, orchestrator: SkillOrchestrator):
        _seed(orchestrator)
        tree = orchestrator.build_tree()
        # Only the root should appear at top level
        assert len(tree) == 1
        root = tree[0]
        assert root.skill_id == "SQL_SKILL"
        assert len(root.children) == 2


class TestResolve:
    def test_resolve_folder_skill(self, orchestrator: SkillOrchestrator):
        _seed(orchestrator)
        result = orchestrator.resolve("SQL stuff")
        assert result["resolved"] is True
        # Should have children listed because the entry is a folder
        assert "children" in result or "skill" in result


class TestHealth:
    def test_health(self, orchestrator: SkillOrchestrator):
        h = orchestrator.health()
        assert h["elasticsearch"] == "ok"
        assert h["embedding_dims"] == 4
