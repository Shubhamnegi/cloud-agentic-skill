"""
MCP Tool Router — dispatches incoming MCP tool calls to the
SkillOrchestrator and formats responses through the MCPAdapter.
"""
from __future__ import annotations

from typing import Any

from app.mcp.adapter import MCPAdapter
from app.services.orchestrator import SkillOrchestrator


class MCPToolRouter:
    """Receives raw MCP tool-call payloads and returns formatted results."""

    def __init__(self, orchestrator: SkillOrchestrator):
        self._orch = orchestrator
        self._adapter = MCPAdapter()

    def list_tools(self) -> list[dict[str, Any]]:
        """Return the tool catalogue."""
        return MCPAdapter.tool_definitions()

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call and return a formatted MCP response."""
        if name == "find_relevant_skill":
            return self._find(arguments)
        if name == "load_instruction":
            return self._load(arguments)
        if name == "list_sub_skills":
            return self._list_children(arguments)
        return {"error": f"Unknown tool: {name}"}

    # ── handlers ──────────────────────────────────────────────

    def _find(self, args: dict) -> dict:
        query = args["query"]
        k = args.get("k", 3)
        results = self._orch.discover(query, k=k)
        return self._adapter.format_discovery([r.model_dump() for r in results])

    def _load(self, args: dict) -> dict:
        skill = self._orch.get_skill(args["skill_id"], include_instruction=True)
        if skill is None:
            return {"error": f"Skill '{args['skill_id']}' not found."}
        return self._adapter.format_instruction(skill.model_dump())

    def _list_children(self, args: dict) -> dict:
        children = self._orch.get_sub_skills(args["skill_id"])
        return self._adapter.format_sub_skills([c.model_dump() for c in children])
