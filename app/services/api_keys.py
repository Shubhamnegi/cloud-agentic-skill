"""
API-Key management service.

Generates, validates and revokes API keys used for MCP authentication.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from app.core.interfaces import APIKeyRepository
from app.core.models import APIKeyCreate, APIKeyCreated, APIKeyRead


class APIKeyService:
    """Manages API keys stored in Elasticsearch."""

    def __init__(self, repo: APIKeyRepository):
        self._repo = repo

    @staticmethod
    def _hash(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()

    def create_key(self, payload: APIKeyCreate) -> APIKeyCreated:
        raw_key = secrets.token_urlsafe(48)
        key_id = secrets.token_hex(8)
        doc = {
            "key_id": key_id,
            "key_hash": self._hash(raw_key),
            "name": payload.name,
            "prefix": raw_key[:8],
            "scopes": payload.scopes,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._repo.store_key(doc)
        return APIKeyCreated(
            key_id=key_id,
            name=payload.name,
            prefix=raw_key[:8],
            scopes=payload.scopes,
            created_at=doc["created_at"],
            full_key=raw_key,
        )

    def validate_key(self, raw_key: str) -> dict | None:
        """Return the key doc if valid, else None."""
        key_hash = self._hash(raw_key)
        return self._repo.get_key_by_hash(key_hash)

    def list_keys(self) -> list[APIKeyRead]:
        return [
            APIKeyRead(
                key_id=k["key_id"],
                name=k.get("name", ""),
                prefix=k.get("prefix", ""),
                scopes=k.get("scopes", []),
                created_at=k.get("created_at", ""),
            )
            for k in self._repo.list_keys()
        ]

    def revoke_key(self, key_id: str) -> bool:
        return self._repo.revoke_key(key_id)
