"""
Pydantic models for the Skill and User entities.
"""
from __future__ import annotations
from pydantic import BaseModel, Field


# ─── Skill Models ───────────────────────────────────────────────

class SkillBase(BaseModel):
    """Base fields shared by create and read operations."""
    skill_id: str = Field(..., description="Unique identifier, e.g. SQL_SKILL_MIGRATION")
    summary: str = Field(..., description="Short human-readable description")
    is_folder: bool = Field(False, description="True if this skill is a branch with sub-skills")
    sub_skills: list[str] = Field(default_factory=list, description="List of child skill_ids")
    instruction: str = Field("", description="Detailed markdown instruction content")


class SkillCreate(SkillBase):
    """Payload for creating / updating a skill."""
    pass


class SkillRead(SkillBase):
    """Response model returned from the API."""
    pass


class SkillDiscovery(BaseModel):
    """Lightweight result returned from vector search (no instruction)."""
    skill_id: str
    summary: str
    sub_skills: list[str] = Field(default_factory=list)
    score: float = Field(0.0, description="Relevance score from search")


class SkillTree(BaseModel):
    """Recursive tree node used by the dashboard."""
    skill_id: str
    summary: str
    is_folder: bool
    children: list[SkillTree] = Field(default_factory=list)


# ─── User / Auth Models ────────────────────────────────────────

class UserBase(BaseModel):
    username: str
    role: str = Field("viewer", description="admin | editor | viewer")
    allowed_skills: list[str] = Field(default_factory=list)


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    pass


class TokenPayload(BaseModel):
    sub: str  # username
    role: str
    scopes: list[str] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── API Key Models ────────────────────────────────────────────

class APIKeyCreate(BaseModel):
    name: str = Field(..., description="Friendly name for the API key")
    scopes: list[str] = Field(default_factory=list, description="Skill scopes this key grants")


class APIKeyRead(BaseModel):
    key_id: str
    name: str
    prefix: str = Field(..., description="First 8 chars of the key for identification")
    scopes: list[str] = Field(default_factory=list)
    created_at: str


class APIKeyCreated(APIKeyRead):
    """Returned only once at creation time — includes the full key."""
    full_key: str
