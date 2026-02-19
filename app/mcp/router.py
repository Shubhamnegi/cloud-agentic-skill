"""
MCP Tool Router — dispatches incoming MCP tool calls to the
SkillOrchestrator and formats responses through the MCPAdapter.

Two dispatch paths:
  call_tool()      — legacy REST path, returns rich dicts
  handle_jsonrpc() — MCP-spec JSON-RPC 2.0 path used by mcp-remote /
                     Claude Desktop / any standard MCP client
"""
from __future__ import annotations

from typing import Any

from app.mcp.adapter import MCPAdapter
from app.services.orchestrator import SkillOrchestrator

# MCP protocol version advertised during initialize handshake
_PROTOCOL_VERSION = "2024-11-05"


class MCPToolRouter:
    """Receives raw MCP tool-call payloads and returns formatted results."""

    def __init__(self, orchestrator: SkillOrchestrator):
        self._orch = orchestrator
        self._adapter = MCPAdapter()

    # ── Tool catalogue ─────────────────────────────────────────────────────

    def list_tools(self) -> list[dict[str, Any]]:
        """Return the tool catalogue (used by both REST and JSON-RPC paths)."""
        return MCPAdapter.tool_definitions()

    # ── Legacy REST path ───────────────────────────────────────────────────

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call and return a formatted MCP response (REST)."""
        if name == "find_relevant_skill":
            return self._find(arguments)
        if name == "load_instruction":
            return self._load(arguments)
        if name == "list_sub_skills":
            return self._list_children(arguments)
        return {"error": f"Unknown tool: {name}"}

    # ── JSON-RPC 2.0 path  (POST /mcp) ────────────────────────────────────

    def handle_jsonrpc(self, body: dict[str, Any]) -> dict[str, Any]:
        """
        Handle a single JSON-RPC 2.0 request and return a JSON-RPC response.

        Supported methods:
          initialize   — capability handshake required by MCP clients
          tools/list   — return the tool catalogue
          tools/call   — invoke a tool and return MCP content
        """
        rpc_id = body.get("id")
        method = body.get("method", "")
        params: dict = body.get("params") or {}

        def _ok(result: Any) -> dict:
            return {"jsonrpc": "2.0", "id": rpc_id, "result": result}

        def _err(code: int, message: str) -> dict:
            return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}

        # ── initialize ────────────────────────────────────────
        if method == "initialize":
            return _ok({
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "cloud-agentic-skill", "version": "1.0.0"},
            })

        # ── tools/list ────────────────────────────────────────
        if method == "tools/list":
            return _ok({"tools": self.list_tools()})

        # ── tools/call ────────────────────────────────────────
        if method == "tools/call":
            name = params.get("name")
            if not name:
                return _err(-32602, "Missing required param: 'name'")
            arguments: dict = params.get("arguments") or {}
            result = self._call_tool_mcp(name, arguments)
            if "error" in result:
                return _err(-32603, result["error"])
            return _ok(result)

        # ── unknown method ────────────────────────────────────
        return _err(-32601, f"Method not found: '{method}'")

    # ── Internal: REST handlers ────────────────────────────────────────────

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

    # ── Internal: JSON-RPC / MCP-spec handlers ─────────────────────────────

    def _call_tool_mcp(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch and return a proper MCP content response."""
        if name == "find_relevant_skill":
            query = arguments.get("query")
            if not query:
                return {"error": "Missing required argument: 'query'"}
            k = arguments.get("k", 3)
            results = self._orch.discover(query, k=k)
            return self._adapter.format_discovery_content(
                [r.model_dump() for r in results]
            )

        if name == "load_instruction":
            skill_id = arguments.get("skill_id")
            if not skill_id:
                return {"error": "Missing required argument: 'skill_id'"}
            skill = self._orch.get_skill(skill_id, include_instruction=True)
            if skill is None:
                return {"error": f"Skill '{skill_id}' not found."}
            return self._adapter.format_instruction_content(skill.model_dump())

        if name == "list_sub_skills":
            skill_id = arguments.get("skill_id")
            if not skill_id:
                return {"error": "Missing required argument: 'skill_id'"}
            children = self._orch.get_sub_skills(skill_id)
            return self._adapter.format_sub_skills_content(
                [c.model_dump() for c in children]
            )

        return {"error": f"Unknown tool: '{name}'"}
