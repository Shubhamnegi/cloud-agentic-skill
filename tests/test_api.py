"""
Integration tests for the FastAPI endpoints using in-memory fakes.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.core.config import Settings
from app.core.models import SkillCreate
from app.main import create_app
from app.mcp.router import MCPToolRouter
from app.services.api_keys import APIKeyService
from app.services.auth import AuthService
from app.services.orchestrator import SkillOrchestrator
from tests.fakes import (
    FakeAPIKeyRepository,
    FakeEmbeddingProvider,
    FakeSkillRepository,
    FakeUserRepository,
)


@pytest.fixture
def client():
    """Build a TestClient with in-memory fakes (no Elasticsearch needed)."""
    settings = Settings(secret_key="test-secret")
    embedding = FakeEmbeddingProvider(dims=4)
    skill_repo = FakeSkillRepository()
    user_repo = FakeUserRepository()
    key_repo = FakeAPIKeyRepository()

    orch = SkillOrchestrator(embedding, skill_repo)
    auth = AuthService(user_repo, skill_repo, settings)
    api_key_svc = APIKeyService(key_repo)
    mcp = MCPToolRouter(orch)

    # Create default admin
    auth.ensure_default_admin(settings)

    # Override deps
    app = create_app()
    app.dependency_overrides[deps.get_orchestrator] = lambda: orch
    app.dependency_overrides[deps.get_auth] = lambda: auth
    app.dependency_overrides[deps.get_api_key_service] = lambda: api_key_svc
    app.dependency_overrides[deps.get_mcp_router] = lambda: mcp

    return TestClient(app)


def _admin_token(client: TestClient) -> str:
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestHealth:
    def test_health_endpoint(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["elasticsearch"] == "ok"


class TestAuth:
    def test_login(self, client: TestClient):
        r = client.post("/auth/login", json={"username": "admin", "password": "admin"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_fail(self, client: TestClient):
        r = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401

    def test_register_requires_admin(self, client: TestClient):
        r = client.post(
            "/auth/register",
            json={"username": "test", "password": "p", "role": "viewer"},
        )
        # No auth header → 422 (missing header)
        assert r.status_code == 422

    def test_register_with_admin(self, client: TestClient):
        tok = _admin_token(client)
        r = client.post(
            "/auth/register",
            json={"username": "viewer1", "password": "p", "role": "viewer", "allowed_skills": ["SQL_SKILL"]},
            headers=_auth_headers(tok),
        )
        assert r.status_code == 201
        assert r.json()["username"] == "viewer1"


class TestSkills:
    def test_create_and_list(self, client: TestClient):
        tok = _admin_token(client)
        h = _auth_headers(tok)
        # Create
        r = client.post("/skills/", json={
            "skill_id": "TEST_SKILL",
            "summary": "Test skill",
            "is_folder": False,
            "sub_skills": [],
            "instruction": "# Test\nContent.",
        }, headers=h)
        assert r.status_code == 201
        # List
        r = client.get("/skills/")
        assert r.status_code == 200
        ids = [s["skill_id"] for s in r.json()]
        assert "TEST_SKILL" in ids

    def test_get_skill(self, client: TestClient):
        tok = _admin_token(client)
        client.post("/skills/", json={
            "skill_id": "X", "summary": "x", "is_folder": False, "sub_skills": [], "instruction": "ix",
        }, headers=_auth_headers(tok))
        r = client.get("/skills/X")
        assert r.status_code == 200
        assert r.json()["skill_id"] == "X"

    def test_get_skill_not_found(self, client: TestClient):
        r = client.get("/skills/NOPE")
        assert r.status_code == 404

    def test_delete(self, client: TestClient):
        tok = _admin_token(client)
        h = _auth_headers(tok)
        client.post("/skills/", json={
            "skill_id": "DEL", "summary": "d", "is_folder": False, "sub_skills": [], "instruction": "",
        }, headers=h)
        r = client.delete("/skills/DEL", headers=h)
        assert r.status_code == 204

    def test_search(self, client: TestClient):
        tok = _admin_token(client)
        client.post("/skills/", json={
            "skill_id": "S1", "summary": "search me", "is_folder": False, "sub_skills": [], "instruction": "",
        }, headers=_auth_headers(tok))
        r = client.get("/skills/search", params={"q": "search"})
        assert r.status_code == 200


class TestAPIKeys:
    def test_create_and_list(self, client: TestClient):
        tok = _admin_token(client)
        h = _auth_headers(tok)
        r = client.post("/api-keys/", json={"name": "test-key", "scopes": ["SQL_SKILL"]}, headers=h)
        assert r.status_code == 201
        assert "full_key" in r.json()

        r = client.get("/api-keys/", headers=h)
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_revoke(self, client: TestClient):
        tok = _admin_token(client)
        h = _auth_headers(tok)
        cr = client.post("/api-keys/", json={"name": "k2", "scopes": []}, headers=h)
        key_id = cr.json()["key_id"]
        r = client.delete(f"/api-keys/{key_id}", headers=h)
        assert r.status_code == 204


class TestMCP:
    def test_mcp_requires_api_key(self, client: TestClient):
        r = client.get("/mcp/tools")
        assert r.status_code == 422  # missing header

    def test_mcp_tools_with_key(self, client: TestClient):
        tok = _admin_token(client)
        h = _auth_headers(tok)
        # Create an API key
        cr = client.post("/api-keys/", json={"name": "mcp", "scopes": []}, headers=h)
        api_key = cr.json()["full_key"]

        r = client.get("/mcp/tools", headers={"X-API-Key": api_key})
        assert r.status_code == 200
        names = {t["name"] for t in r.json()}
        assert "find_relevant_skill" in names

    def test_mcp_tool_call(self, client: TestClient):
        tok = _admin_token(client)
        h = _auth_headers(tok)
        # Seed a skill
        client.post("/skills/", json={
            "skill_id": "MCP_TEST", "summary": "test", "is_folder": False, "sub_skills": [], "instruction": "hi",
        }, headers=h)
        # Create API key
        cr = client.post("/api-keys/", json={"name": "mcp2", "scopes": []}, headers=h)
        api_key = cr.json()["full_key"]

        r = client.post(
            "/mcp/tools/call",
            json={"name": "load_instruction", "arguments": {"skill_id": "MCP_TEST"}},
            headers={"X-API-Key": api_key},
        )
        assert r.status_code == 200
        assert r.json()["type"] == "skill_instruction"
