"""
Unit tests for AuthService — runs entirely in-memory.
"""
from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.models import UserCreate
from app.services.auth import AuthService
from tests.fakes import FakeSkillRepository, FakeUserRepository


@pytest.fixture
def auth() -> AuthService:
    settings = Settings(secret_key="test-secret", access_token_expire_minutes=5)
    return AuthService(
        user_repo=FakeUserRepository(),
        skill_repo=FakeSkillRepository(),
        settings=settings,
    )


class TestRegistration:
    def test_register_and_authenticate(self, auth: AuthService):
        auth.register(UserCreate(username="alice", password="pass123", role="viewer"))
        token = auth.authenticate("alice", "pass123")
        assert token is not None
        assert token.access_token

    def test_wrong_password(self, auth: AuthService):
        auth.register(UserCreate(username="bob", password="secret"))
        assert auth.authenticate("bob", "wrong") is None

    def test_nonexistent_user(self, auth: AuthService):
        assert auth.authenticate("ghost", "pass") is None


class TestTokens:
    def test_decode_valid_token(self, auth: AuthService):
        auth.register(UserCreate(username="carol", password="p", role="admin", allowed_skills=["SQL_SKILL"]))
        tok = auth.authenticate("carol", "p")
        payload = auth.decode_token(tok.access_token)
        assert payload is not None
        assert payload.sub == "carol"
        assert payload.role == "admin"
        assert "skill:SQL_SKILL" in payload.scopes

    def test_decode_invalid_token(self, auth: AuthService):
        assert auth.decode_token("garbage.token.here") is None


class TestPermissions:
    def test_is_skill_accessible_direct(self, auth: AuthService):
        assert auth.is_skill_accessible("SQL_SKILL", ["SQL_SKILL"])

    def test_admin_unrestricted(self, auth: AuthService):
        # empty allowed_skills means admin / unrestricted
        assert auth.is_skill_accessible("ANY_SKILL", [])

    def test_not_accessible(self, auth: AuthService):
        assert not auth.is_skill_accessible("SECRET", ["SQL_SKILL"])


class TestUserManagement:
    def test_list_and_delete(self, auth: AuthService):
        auth.register(UserCreate(username="u1", password="p"))
        auth.register(UserCreate(username="u2", password="p"))
        assert len(auth.list_users()) == 2
        auth.delete_user("u1")
        assert len(auth.list_users()) == 1
