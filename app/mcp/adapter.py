"""
MCP Adapter — translates internal data into the Model Context Protocol
tool / resource format that LLMs (Claude, GPT-4, …) understand.
"""
from __future__ import annotations

from typing import Any


class MCPAdapter:
    """Adapter that formats internal data for MCP-compatible responses."""

    # ── Tool Definitions ──────────────────────────────────────

    @staticmethod
    def tool_definitions() -> list[dict[str, Any]]:
        """Return the MCP tool catalogue that an Agent can call."""
        return [
            {
                "name": "find_relevant_skill",
                "description": (
                    "Search the skill database for capabilities matching a "
                    "natural-language query. Returns lightweight summaries — "
                    "call load_instruction to get the full content."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural-language description of what you need.",
                        },
                        "k": {
                            "type": "integer",
                            "description": "Number of results to return (default 3).",
                            "default": 3,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "load_instruction",
                "description": (
                    "Fetch the full instruction content for a specific skill "
                    "by its skill_id. Use this after discovery to get the "
                    "detailed Markdown guide."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "The unique identifier of the skill to load.",
                        }
                    },
                    "required": ["skill_id"],
                },
            },
            {
                "name": "list_sub_skills",
                "description": (
                    "List the immediate children of a folder-type skill. "
                    "Returns summaries only."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "The parent skill whose children to list.",
                        }
                    },
                    "required": ["skill_id"],
                },
            },
        ]

    # ── Response Formatters ───────────────────────────────────

    @staticmethod
    def format_discovery(skills: list[dict]) -> dict[str, Any]:
        """Format vector-search results for MCP transport."""
        return {
            "type": "skill_discovery",
            "results": [
                {
                    "skill_id": s.get("skill_id") or s.get("id"),
                    "summary": s.get("summary", ""),
                    "has_children": bool(s.get("sub_skills")),
                    "score": s.get("score", 0.0),
                }
                for s in skills
            ],
        }

    @staticmethod
    def format_instruction(skill: dict) -> dict[str, Any]:
        """Format a full skill document for MCP transport."""
        return {
            "type": "skill_instruction",
            "skill_id": skill.get("skill_id", ""),
            "summary": skill.get("summary", ""),
            "content": skill.get("instruction", ""),
            "sub_skills": skill.get("sub_skills", []),
        }

    @staticmethod
    def format_sub_skills(children: list[dict]) -> dict[str, Any]:
        """Format a list of child skills for MCP transport."""
        return {
            "type": "skill_children",
            "children": [
                {
                    "skill_id": c.get("skill_id", ""),
                    "summary": c.get("summary", ""),
                    "has_children": bool(c.get("sub_skills")),
                }
                for c in children
            ],
        }
