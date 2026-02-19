"""
Skill CRUD & search endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_orchestrator, require_admin, require_token
from app.core.models import SkillCreate, SkillDiscovery, SkillRead, SkillTree, TokenPayload
from app.services.orchestrator import SkillOrchestrator

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/search", response_model=list[SkillDiscovery])
def search_skills(
    q: str,
    k: int = 3,
    orch: SkillOrchestrator = Depends(get_orchestrator),
):
    """Semantic search over skill descriptions."""
    return orch.discover(q, k=k)


@router.get("/tree", response_model=list[SkillTree])
def get_skill_tree(orch: SkillOrchestrator = Depends(get_orchestrator)):
    """Return the full skill tree (for dashboard visualisation)."""
    return orch.build_tree()


@router.get("/", response_model=list[SkillDiscovery])
def list_skills(orch: SkillOrchestrator = Depends(get_orchestrator)):
    """List all skills (lightweight, no instructions)."""
    return orch.list_skills()


@router.get("/{skill_id}", response_model=SkillRead)
def get_skill(
    skill_id: str,
    include_instruction: bool = True,
    orch: SkillOrchestrator = Depends(get_orchestrator),
):
    skill = orch.get_skill(skill_id, include_instruction=include_instruction)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.get("/{skill_id}/children", response_model=list[SkillDiscovery])
def get_children(
    skill_id: str,
    orch: SkillOrchestrator = Depends(get_orchestrator),
):
    return orch.get_sub_skills(skill_id)


@router.post("/", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(
    payload: SkillCreate,
    orch: SkillOrchestrator = Depends(get_orchestrator),
    _admin: TokenPayload = Depends(require_admin),
):
    return orch.create_or_update_skill(payload)


@router.put("/{skill_id}", response_model=SkillRead)
def update_skill(
    skill_id: str,
    payload: SkillCreate,
    orch: SkillOrchestrator = Depends(get_orchestrator),
    _admin: TokenPayload = Depends(require_admin),
):
    if payload.skill_id != skill_id:
        raise HTTPException(400, "skill_id in path and body must match")
    return orch.create_or_update_skill(payload)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: str,
    orch: SkillOrchestrator = Depends(get_orchestrator),
    _admin: TokenPayload = Depends(require_admin),
):
    if not orch.delete_skill(skill_id):
        raise HTTPException(404, "Skill not found")
