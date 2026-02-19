"""
Unit tests for the MCP Adapter and Router — runs entirely in-memory.
"""
from __future__ import annotations

import pytest

from app.core.models import SkillCreate
from app.mcp.adapter import MCPAdapter
from app.mcp.router import MCPToolRouter
from app.services.orchestrator import SkillOrchestrator
from tests.fakes import FakeEmbeddingProvider, FakeSkillRepository


@pytest.fixture
def mcp_router() -> MCPToolRouter:
    orch = SkillOrchestrator(
        embedding=FakeEmbeddingProvider(dims=4),
        repository=FakeSkillRepository(),
    )
    # Seed data
    orch.create_or_update_skill(SkillCreate(
        skill_id="SQL_SKILL",
        summary="SQL skills",
        is_folder=True,
        sub_skills=["SQL_MIGRATION"],
        instruction="Parent skill.",
    ))
    orch.create_or_update_skill(SkillCreate(
        skill_id="SQL_MIGRATION",
        summary="Migration and sharding",
        is_folder=False,
        instruction="# Migration\nSharding details here.",
    ))
    return MCPToolRouter(orch)


class TestToolDefinitions:
    def test_list_tools(self, mcp_router: MCPToolRouter):
        tools = mcp_router.list_tools()
        names = {t["name"] for t in tools}
        assert "find_relevant_skill" in names
        assert "load_instruction" in names
        assert "list_sub_skills" in names


class TestToolCalls:
    def test_find_relevant_skill(self, mcp_router: MCPToolRouter):
        result = mcp_router.call_tool("find_relevant_skill", {"query": "sharding", "k": 2})
        assert result["type"] == "skill_discovery"
        assert len(result["results"]) <= 2

    def test_load_instruction(self, mcp_router: MCPToolRouter):
        result = mcp_router.call_tool("load_instruction", {"skill_id": "SQL_MIGRATION"})
        assert result["type"] == "skill_instruction"
        assert "Migration" in result["content"]

    def test_load_instruction_not_found(self, mcp_router: MCPToolRouter):
        result = mcp_router.call_tool("load_instruction", {"skill_id": "NONEXISTENT"})
        assert "error" in result

    def test_list_sub_skills(self, mcp_router: MCPToolRouter):
        result = mcp_router.call_tool("list_sub_skills", {"skill_id": "SQL_SKILL"})
        assert result["type"] == "skill_children"
        ids = {c["skill_id"] for c in result["children"]}
        assert "SQL_MIGRATION" in ids

    def test_unknown_tool(self, mcp_router: MCPToolRouter):
        result = mcp_router.call_tool("nonexistent_tool", {})
        assert "error" in result


class TestMCPAdapter:
    def test_format_discovery(self):
        skills = [{"skill_id": "A", "summary": "aaa", "sub_skills": ["B"], "score": 0.9}]
        out = MCPAdapter.format_discovery(skills)
        assert out["type"] == "skill_discovery"
        assert out["results"][0]["has_children"] is True

    def test_format_instruction(self):
        skill = {"skill_id": "A", "summary": "aaa", "instruction": "content", "sub_skills": []}
        out = MCPAdapter.format_instruction(skill)
        assert out["content"] == "content"
