"""
API-key management endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_api_key_service, require_admin
from app.core.models import APIKeyCreate, APIKeyCreated, APIKeyRead, TokenPayload
from app.services.api_keys import APIKeyService

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("/", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
def create_key(
    body: APIKeyCreate,
    svc: APIKeyService = Depends(get_api_key_service),
    _admin: TokenPayload = Depends(require_admin),
):
    """Generate a new API key (shown only once)."""
    return svc.create_key(body)


@router.get("/", response_model=list[APIKeyRead])
def list_keys(
    svc: APIKeyService = Depends(get_api_key_service),
    _admin: TokenPayload = Depends(require_admin),
):
    return svc.list_keys()


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_key(
    key_id: str,
    svc: APIKeyService = Depends(get_api_key_service),
    _admin: TokenPayload = Depends(require_admin),
):
    if not svc.revoke_key(key_id):
        raise HTTPException(404, "Key not found")
