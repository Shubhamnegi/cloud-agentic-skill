"""
MCP protocol endpoints.

Standard MCP (JSON-RPC 2.0)
  POST /mcp          ← use this with mcp-remote, Claude Desktop, any MCP client

Legacy REST (kept for backward compatibility)
  GET  /mcp/tools
  POST /mcp/tools/call

All endpoints are protected by API-key authentication via X-API-Key header.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.deps import get_mcp_router, require_api_key
from app.mcp.router import MCPToolRouter

router = APIRouter(prefix="/mcp", tags=["mcp"])


# ── JSON-RPC 2.0 request model ─────────────────────────────────────────────


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Any = None
    method: str
    params: dict[str, Any] = {}


# ── Legacy REST request model ──────────────────────────────────────────────


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = {}


# ── Standard MCP endpoint (JSON-RPC 2.0) ──────────────────────────────────


@router.post("", summary="MCP JSON-RPC 2.0 endpoint (use this with mcp-remote / Claude Desktop)")
def mcp_jsonrpc(
    body: JSONRPCRequest,
    mcp: MCPToolRouter = Depends(get_mcp_router),
    _key: dict = Depends(require_api_key),
):
    """
    Single JSON-RPC 2.0 entry-point compatible with any standard MCP client.

    Supported methods:
      - initialize   — capability handshake
      - tools/list   — list available tools
      - tools/call   — invoke a tool

    Example – list tools:
        curl -X POST http://localhost:8000/mcp \\
          -H "X-API-Key: <key>" \\
          -H "Content-Type: application/json" \\
          -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

    Example – call a tool:
        curl -X POST http://localhost:8000/mcp \\
          -H "X-API-Key: <key>" \\
          -H "Content-Type: application/json" \\
          -d '{
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "find_relevant_skill", "arguments": {"query": "SQL sharding"}}
          }'
    """
    return mcp.handle_jsonrpc(body.model_dump())


# ── Legacy REST endpoints (backward compatible) ────────────────────────────


@router.get("/tools", summary="[Legacy] List MCP tools (REST)")
def list_tools(
    mcp: MCPToolRouter = Depends(get_mcp_router),
    _key: dict = Depends(require_api_key),
):
    """Return the catalogue of available MCP tools (legacy REST format)."""
    return mcp.list_tools()


@router.post("/tools/call", summary="[Legacy] Invoke an MCP tool (REST)")
def call_tool(
    body: ToolCallRequest,
    mcp: MCPToolRouter = Depends(get_mcp_router),
    _key: dict = Depends(require_api_key),
):
    """Invoke an MCP tool by name (legacy REST format)."""
    return mcp.call_tool(body.name, body.arguments)
