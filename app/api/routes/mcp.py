"""
MCP protocol endpoints — tool listing and invocation.
Protected by API-key authentication.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_mcp_router, require_api_key
from app.mcp.router import MCPToolRouter

router = APIRouter(prefix="/mcp", tags=["mcp"])


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = {}


@router.get("/tools")
def list_tools(
    mcp: MCPToolRouter = Depends(get_mcp_router),
    _key: dict = Depends(require_api_key),
):
    """Return the catalogue of available MCP tools."""
    return mcp.list_tools()


@router.post("/tools/call")
def call_tool(
    body: ToolCallRequest,
    mcp: MCPToolRouter = Depends(get_mcp_router),
    _key: dict = Depends(require_api_key),
):
    """Invoke an MCP tool by name."""
    return mcp.call_tool(body.name, body.arguments)
