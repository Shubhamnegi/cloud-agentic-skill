"""
In-memory fakes for unit testing — no Elasticsearch required.
"""
from __future__ import annotations

from app.core.interfaces import APIKeyRepository, EmbeddingProvider, SkillRepository, UserRepository


class FakeEmbeddingProvider(EmbeddingProvider):
    """Returns a fixed-dimension zero vector for any input."""

    def __init__(self, dims: int = 4):
        self._dims = dims

    def encode(self, text: str) -> list[float]:
        # Simple deterministic "hash" for testing
        val = float(hash(text) % 1000) / 1000.0
        return [val] * self._dims

    def get_dimensions(self) -> int:
        return self._dims


class FakeSkillRepository(SkillRepository):
    """In-memory skill store."""

    def __init__(self):
        self._store: dict[str, dict] = {}

    def ensure_index(self) -> None:
        pass

    def search_by_vector(self, vector: list[float], k: int = 3) -> list[dict]:
        # Return all docs (no real vector similarity)
        results = []
        for doc in list(self._store.values())[:k]:
            results.append({**doc, "score": 1.0})
        return results

    def get_by_id(self, skill_id: str, fields: list[str] | None = None) -> dict | None:
        doc = self._store.get(skill_id)
        if doc is None:
            return None
        if fields:
            return {k: v for k, v in doc.items() if k in fields}
        return dict(doc)

    def upsert(self, skill: dict) -> None:
        self._store[skill["skill_id"]] = skill

    def delete(self, skill_id: str) -> bool:
        return self._store.pop(skill_id, None) is not None

    def list_all(self, size: int = 100) -> list[dict]:
        return [
            {k: v for k, v in doc.items() if k != "instruction" and k != "skill_desc_vector"}
            for doc in list(self._store.values())[:size]
        ]

    def health_check(self) -> bool:
        return True


class FakeUserRepository(UserRepository):
    """In-memory user store."""

    def __init__(self):
        self._store: dict[str, dict] = {}

    def ensure_index(self) -> None:
        pass

    def get_user(self, username: str) -> dict | None:
        return self._store.get(username)

    def create_user(self, user: dict) -> None:
        self._store[user["username"]] = user

    def update_user(self, username: str, fields: dict) -> None:
        if username in self._store:
            self._store[username].update(fields)

    def list_users(self) -> list[dict]:
        return list(self._store.values())

    def delete_user(self, username: str) -> bool:
        return self._store.pop(username, None) is not None


class FakeAPIKeyRepository(APIKeyRepository):
    """In-memory API-key store."""

    def __init__(self):
        self._store: dict[str, dict] = {}

    def ensure_index(self) -> None:
        pass

    def store_key(self, key_doc: dict) -> None:
        self._store[key_doc["key_id"]] = key_doc

    def get_key_by_hash(self, key_hash: str) -> dict | None:
        for doc in self._store.values():
            if doc.get("key_hash") == key_hash:
                return doc
        return None

    def list_keys(self) -> list[dict]:
        return list(self._store.values())

    def revoke_key(self, key_id: str) -> bool:
        return self._store.pop(key_id, None) is not None
