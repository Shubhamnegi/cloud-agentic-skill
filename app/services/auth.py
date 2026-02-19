"""
Authentication & authorisation service.

Handles password hashing, JWT creation / validation, and
hierarchical permission checks for the skill tree.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import Settings
from app.core.interfaces import SkillRepository, UserRepository
from app.core.models import TokenPayload, TokenResponse, UserCreate, UserRead


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


class AuthService:
    """Manages users, tokens and permission checks."""

    def __init__(
        self,
        user_repo: UserRepository,
        skill_repo: SkillRepository,
        settings: Settings,
    ):
        self._users = user_repo
        self._skills = skill_repo
        self._secret = settings.secret_key
        self._expire = settings.access_token_expire_minutes

    # ── User management ───────────────────────────────────────

    def register(self, payload: UserCreate) -> UserRead:
        doc = {
            "username": payload.username,
            "password_hash": _hash_password(payload.password),
            "role": payload.role,
            "allowed_skills": payload.allowed_skills,
        }
        self._users.create_user(doc)
        return UserRead(
            username=payload.username,
            role=payload.role,
            allowed_skills=payload.allowed_skills,
        )

    def authenticate(self, username: str, password: str) -> TokenResponse | None:
        user = self._users.get_user(username)
        if not user or not _verify_password(password, user["password_hash"]):
            return None
        scopes = [f"skill:{s}" for s in user.get("allowed_skills", [])]
        payload = {
            "sub": username,
            "role": user["role"],
            "scopes": scopes,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=self._expire),
        }
        token = jwt.encode(payload, self._secret, algorithm="HS256")
        return TokenResponse(access_token=token)

    def decode_token(self, token: str) -> TokenPayload | None:
        try:
            data = jwt.decode(token, self._secret, algorithms=["HS256"])
            return TokenPayload(**data)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    # ── Permission helpers ────────────────────────────────────

    def is_skill_accessible(self, skill_id: str, allowed_skills: list[str]) -> bool:
        """Check if *skill_id* is a descendant of any allowed top-level skill."""
        if not allowed_skills:  # empty => unrestricted (admin)
            return True
        if skill_id in allowed_skills:
            return True
        for parent_id in allowed_skills:
            if self._is_descendant(skill_id, parent_id):
                return True
        return False

    def _is_descendant(self, target: str, parent: str, _depth: int = 0) -> bool:
        if _depth > 10:
            return False
        doc = self._skills.get_by_id(parent, fields=["sub_skills"])
        if not doc:
            return False
        subs = doc.get("sub_skills", [])
        if target in subs:
            return True
        return any(self._is_descendant(target, s, _depth + 1) for s in subs)

    def get_all_descendants(self, skill_ids: list[str]) -> list[str]:
        """Return *all* skill_ids reachable from the given roots."""
        result: set[str] = set(skill_ids)
        stack = list(skill_ids)
        while stack:
            current = stack.pop()
            doc = self._skills.get_by_id(current, fields=["sub_skills"])
            if not doc:
                continue
            for child in doc.get("sub_skills", []):
                if child not in result:
                    result.add(child)
                    stack.append(child)
        return sorted(result)

    # ── User listing / update ─────────────────────────────────

    def list_users(self) -> list[UserRead]:
        return [
            UserRead(
                username=u["username"],
                role=u.get("role", "viewer"),
                allowed_skills=u.get("allowed_skills", []),
            )
            for u in self._users.list_users()
        ]

    def update_permissions(self, username: str, allowed_skills: list[str]) -> bool:
        user = self._users.get_user(username)
        if not user:
            return False
        self._users.update_user(username, {"allowed_skills": allowed_skills})
        return True

    def delete_user(self, username: str) -> bool:
        return self._users.delete_user(username)

    def ensure_default_admin(self, settings: Settings) -> None:
        """Create the default admin user if it doesn't exist yet."""
        if self._users.get_user(settings.default_admin_username):
            return
        self.register(
            UserCreate(
                username=settings.default_admin_username,
                password=settings.default_admin_password,
                role="admin",
                allowed_skills=[],
            )
        )
