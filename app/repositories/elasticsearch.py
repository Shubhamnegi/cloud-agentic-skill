"""
Elasticsearch-backed implementations of the repository interfaces.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from opensearchpy import OpenSearch, NotFoundError

from app.core.interfaces import APIKeyRepository, SkillRepository, UserRepository

logger = logging.getLogger(__name__)

_INDEX_CREATE_TIMEOUT = 60  # HTTP socket timeout in seconds for index creation
_INDEX_CREATE_MAX_RETRIES = 3
_INDEX_CREATE_RETRY_DELAY = 5.0  # seconds between retries


def _retry_ensure_index(fn, retries: int = _INDEX_CREATE_MAX_RETRIES, delay: float = _INDEX_CREATE_RETRY_DELAY):
    """Retry wrapper for index creation to handle transient timeouts."""
    import time
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == retries:
                raise
            logger.warning(
                "Index creation failed (attempt %d/%d): %s — retrying in %.1fs …",
                attempt, retries, exc, delay,
            )
            time.sleep(delay)


# ─── Skill Repository ──────────────────────────────────────────

class ElasticsearchSkillRepository(SkillRepository):
    """Concrete skill repository backed by OpenSearch."""

    def __init__(self, es: OpenSearch, index: str = "agent_skills", dims: int = 384):
        self._es = es
        self._index = index
        self._dims = dims

    # -- index management --------------------------------------------------

    def ensure_index(self) -> None:
        def _create():
            if self._es.indices.exists(index=self._index, request_timeout=_INDEX_CREATE_TIMEOUT):
                logger.info("Index '%s' already exists.", self._index)
                return
            self._es.indices.create(
                index=self._index,
                body={
                    "settings": {
                        "index.knn": True,
                    },
                    "mappings": {
                        "properties": {
                            "skill_id": {"type": "keyword"},
                            "skill_desc_vector": {
                                "type": "knn_vector",
                                "dimension": self._dims,
                                "method": {
                                    "name": "hnsw",
                                    "space_type": "cosinesimil",
                                    "engine": "nmslib",
                                    "parameters": {"ef_construction": 128, "m": 16},
                                },
                            },
                            "summary": {"type": "text", "index": False},
                            "is_folder": {"type": "boolean"},
                            "sub_skills": {"type": "keyword"},
                            "instruction": {"type": "text", "index": False},
                        }
                    },
                },
                request_timeout=_INDEX_CREATE_TIMEOUT,
            )
            logger.info("Index '%s' created (dims=%d).", self._index, self._dims)

        _retry_ensure_index(_create)

    # -- queries -----------------------------------------------------------

    def search_by_vector(self, vector: list[float], k: int = 3) -> list[dict]:
        resp = self._es.search(
            index=self._index,
            body={
                "size": k,
                "query": {
                    "knn": {
                        "skill_desc_vector": {
                            "vector": vector,
                            "k": k,
                        }
                    }
                },
                "_source": ["skill_id", "summary", "sub_skills", "is_folder"],
            },
        )
        results = []
        for hit in resp["hits"]["hits"]:
            doc = hit["_source"]
            doc["score"] = hit["_score"]
            results.append(doc)
        return results

    def get_by_id(self, skill_id: str, fields: list[str] | None = None) -> dict | None:
        try:
            kwargs: dict = {"index": self._index, "id": skill_id}
            if fields:
                kwargs["_source_includes"] = ",".join(fields)
            doc = self._es.get(**kwargs)
            return doc["_source"]
        except NotFoundError:
            return None

    def upsert(self, skill: dict) -> None:
        self._es.index(
            index=self._index,
            id=skill["skill_id"],
            body=skill,
            refresh="wait_for",
        )

    def delete(self, skill_id: str) -> bool:
        try:
            self._es.delete(index=self._index, id=skill_id, refresh="wait_for")
            return True
        except NotFoundError:
            return False

    def list_all(self, size: int = 200) -> list[dict]:
        resp = self._es.search(
            index=self._index,
            body={
                "query": {"match_all": {}},
                "size": size,
                "_source": ["skill_id", "summary", "is_folder", "sub_skills"],
            },
        )
        return [hit["_source"] for hit in resp["hits"]["hits"]]

    def health_check(self) -> bool:
        try:
            return self._es.ping()
        except Exception:
            return False


# ─── User Repository ───────────────────────────────────────────

class ElasticsearchUserRepository(UserRepository):
    """Concrete user repository backed by OpenSearch."""

    def __init__(self, es: OpenSearch, index: str = "skill_users"):
        self._es = es
        self._index = index

    def ensure_index(self) -> None:
        def _create():
            if self._es.indices.exists(index=self._index, request_timeout=_INDEX_CREATE_TIMEOUT):
                return
            self._es.indices.create(
                index=self._index,
                body={
                    "mappings": {
                        "properties": {
                            "username": {"type": "keyword"},
                            "password_hash": {"type": "keyword", "index": False},
                            "role": {"type": "keyword"},
                            "allowed_skills": {"type": "keyword"},
                        }
                    }
                },
                request_timeout=_INDEX_CREATE_TIMEOUT,
            )
            logger.info("User index '%s' created.", self._index)

        _retry_ensure_index(_create)

    def get_user(self, username: str) -> dict | None:
        try:
            doc = self._es.get(index=self._index, id=username)
            return doc["_source"]
        except NotFoundError:
            return None

    def create_user(self, user: dict) -> None:
        self._es.index(
            index=self._index,
            id=user["username"],
            body=user,
            refresh="wait_for",
        )

    def update_user(self, username: str, fields: dict) -> None:
        self._es.update(
            index=self._index,
            id=username,
            body={"doc": fields},
            refresh="wait_for",
        )

    def list_users(self) -> list[dict]:
        resp = self._es.search(
            index=self._index,
            body={
                "query": {"match_all": {}},
                "size": 200,
                "_source": ["username", "role", "allowed_skills"],
            },
        )
        return [hit["_source"] for hit in resp["hits"]["hits"]]

    def delete_user(self, username: str) -> bool:
        try:
            self._es.delete(index=self._index, id=username, refresh="wait_for")
            return True
        except NotFoundError:
            return False


# ─── API Key Repository ────────────────────────────────────────

class ElasticsearchAPIKeyRepository(APIKeyRepository):
    """Concrete API-key repository backed by OpenSearch."""

    def __init__(self, es: OpenSearch, index: str = "skill_api_keys"):
        self._es = es
        self._index = index

    def ensure_index(self) -> None:
        def _create():
            if self._es.indices.exists(index=self._index, request_timeout=_INDEX_CREATE_TIMEOUT):
                return
            self._es.indices.create(
                index=self._index,
                body={
                    "mappings": {
                        "properties": {
                            "key_id": {"type": "keyword"},
                            "key_hash": {"type": "keyword"},
                            "name": {"type": "text", "index": False},
                            "prefix": {"type": "keyword", "index": False},
                            "scopes": {"type": "keyword"},
                            "created_at": {"type": "date"},
                        }
                    }
                },
                request_timeout=_INDEX_CREATE_TIMEOUT,
            )
            logger.info("API-key index '%s' created.", self._index)

        _retry_ensure_index(_create)

    def store_key(self, key_doc: dict) -> None:
        self._es.index(
            index=self._index,
            id=key_doc["key_id"],
            body=key_doc,
            refresh="wait_for",
        )

    def get_key_by_hash(self, key_hash: str) -> dict | None:
        resp = self._es.search(
            index=self._index,
            body={"query": {"term": {"key_hash": key_hash}}, "size": 1},
        )
        hits = resp["hits"]["hits"]
        return hits[0]["_source"] if hits else None

    def list_keys(self) -> list[dict]:
        resp = self._es.search(
            index=self._index,
            body={
                "query": {"match_all": {}},
                "size": 200,
                "_source": ["key_id", "name", "prefix", "scopes", "created_at"],
            },
        )
        return [hit["_source"] for hit in resp["hits"]["hits"]]

    def revoke_key(self, key_id: str) -> bool:
        try:
            self._es.delete(index=self._index, id=key_id, refresh="wait_for")
            return True
        except NotFoundError:
            return False
