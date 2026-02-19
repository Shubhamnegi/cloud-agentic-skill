"""
Abstract interfaces that decouple the business logic from
specific embedding models and database backends.
"""
from __future__ import annotations
from abc import ABC, abstractmethod


# ─── Embedding Provider (Strategy Pattern) ──────────────────────

class EmbeddingProvider(ABC):
    """Abstract interface for embedding models."""

    @abstractmethod
    def encode(self, text: str) -> list[float]:
        """Convert *text* to a vector embedding."""

    @abstractmethod
    def get_dimensions(self) -> int:
        """Return the dimensionality of the embedding vectors."""


# ─── Skill Repository (Repository Pattern) ─────────────────────

class SkillRepository(ABC):
    """Abstract interface for skill storage backends."""

    @abstractmethod
    def ensure_index(self) -> None:
        """Create the underlying storage structure if it doesn't exist."""

    @abstractmethod
    def search_by_vector(
        self, vector: list[float], k: int = 3
    ) -> list[dict]:
        """Find skills matching a query vector."""

    @abstractmethod
    def get_by_id(self, skill_id: str, fields: list[str] | None = None) -> dict | None:
        """Fetch a specific skill by its ID."""

    @abstractmethod
    def upsert(self, skill: dict) -> None:
        """Insert or update a skill document."""

    @abstractmethod
    def delete(self, skill_id: str) -> bool:
        """Delete a skill by its ID. Return True if deleted."""

    @abstractmethod
    def list_all(self, size: int = 100) -> list[dict]:
        """Return all skills (lightweight — no instruction field)."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the underlying store is reachable."""


# ─── User Repository ───────────────────────────────────────────

class UserRepository(ABC):
    """Abstract interface for user storage."""

    @abstractmethod
    def ensure_index(self) -> None: ...

    @abstractmethod
    def get_user(self, username: str) -> dict | None: ...

    @abstractmethod
    def create_user(self, user: dict) -> None: ...

    @abstractmethod
    def update_user(self, username: str, fields: dict) -> None: ...

    @abstractmethod
    def list_users(self) -> list[dict]: ...

    @abstractmethod
    def delete_user(self, username: str) -> bool: ...


# ─── API Key Repository ────────────────────────────────────────

class APIKeyRepository(ABC):
    """Abstract interface for API key storage."""

    @abstractmethod
    def ensure_index(self) -> None: ...

    @abstractmethod
    def store_key(self, key_doc: dict) -> None: ...

    @abstractmethod
    def get_key_by_hash(self, key_hash: str) -> dict | None: ...

    @abstractmethod
    def list_keys(self) -> list[dict]: ...

    @abstractmethod
    def revoke_key(self, key_id: str) -> bool: ...
