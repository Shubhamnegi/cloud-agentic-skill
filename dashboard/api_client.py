"""
api_client.py — Centralised HTTP calls for the Streamlit dashboard.

All functions return (data, error_message).  Callers check whether
`error_message` is None to decide whether to show success or an error
widget.
"""
from __future__ import annotations

from typing import Any

import requests

TIMEOUT = 10  # seconds


# ─── Auth ──────────────────────────────────────────────────────────────────


def login(backend: str, username: str, password: str) -> tuple[str | None, str | None]:
    """Return (access_token, error)."""
    try:
        r = requests.post(
            f"{backend}/auth/login",
            json={"username": username, "password": password},
            timeout=TIMEOUT,
        )
        if r.ok:
            return r.json()["access_token"], None
        return None, f"Login failed ({r.status_code}): {r.text}"
    except requests.ConnectionError:
        return None, "Cannot reach the backend."


# ─── Health ────────────────────────────────────────────────────────────────


def get_health(backend: str) -> tuple[dict | None, str | None]:
    try:
        r = requests.get(f"{backend}/health", timeout=TIMEOUT)
        if r.ok:
            return r.json(), None
        return None, f"Backend returned {r.status_code}"
    except requests.ConnectionError:
        return None, "Cannot reach the backend. Is it running?"


# ─── Skills ────────────────────────────────────────────────────────────────


def search_skills(backend: str, headers: dict, query: str, k: int = 5) -> tuple[list | None, str | None]:
    try:
        r = requests.get(
            f"{backend}/skills/search",
            params={"q": query, "k": k},
            headers=headers,
            timeout=TIMEOUT,
        )
        if r.ok:
            return r.json(), None
        return None, f"Search failed ({r.status_code}): {r.text}"
    except requests.ConnectionError:
        return None, "Backend unreachable."


def get_skill(backend: str, headers: dict, skill_id: str) -> tuple[dict | None, str | None]:
    try:
        r = requests.get(f"{backend}/skills/{skill_id}", headers=headers, timeout=TIMEOUT)
        if r.ok:
            return r.json(), None
        return None, f"Error {r.status_code}: {r.text}"
    except requests.ConnectionError:
        return None, "Backend unreachable."


def get_skill_tree(backend: str, headers: dict) -> tuple[list | None, str | None]:
    try:
        r = requests.get(f"{backend}/skills/tree", headers=headers, timeout=TIMEOUT)
        if r.ok:
            return r.json(), None
        return None, f"Error {r.status_code}: {r.text}"
    except requests.ConnectionError:
        return None, "Backend unreachable."


def upsert_skill(backend: str, headers: dict, payload: dict[str, Any]) -> tuple[dict | None, str | None]:
    try:
        r = requests.post(f"{backend}/skills/", json=payload, headers=headers, timeout=TIMEOUT)
        if r.status_code in (200, 201):
            return r.json(), None
        return None, f"Error {r.status_code}: {r.text}"
    except requests.ConnectionError:
        return None, "Backend unreachable."


def delete_skill(backend: str, headers: dict, skill_id: str) -> tuple[bool, str | None]:
    try:
        r = requests.delete(f"{backend}/skills/{skill_id}", headers=headers, timeout=TIMEOUT)
        if r.status_code == 204:
            return True, None
        return False, f"Error {r.status_code}: {r.text}"
    except requests.ConnectionError:
        return False, "Backend unreachable."


# ─── API Keys ──────────────────────────────────────────────────────────────


def create_api_key(
    backend: str, headers: dict, name: str, scopes: list[str]
) -> tuple[dict | None, str | None]:
    try:
        r = requests.post(
            f"{backend}/api-keys/",
            json={"name": name, "scopes": scopes},
            headers=headers,
            timeout=TIMEOUT,
        )
        if r.status_code == 201:
            return r.json(), None
        return None, f"Error {r.status_code}: {r.text}"
    except requests.ConnectionError:
        return None, "Backend unreachable."


def list_api_keys(backend: str, headers: dict) -> tuple[list | None, str | None]:
    try:
        r = requests.get(f"{backend}/api-keys/", headers=headers, timeout=TIMEOUT)
        if r.ok:
            return r.json(), None
        return None, f"Error {r.status_code}: {r.text}"
    except requests.ConnectionError:
        return None, "Backend unreachable."


def revoke_api_key(backend: str, headers: dict, key_id: str) -> tuple[bool, str | None]:
    try:
        r = requests.delete(f"{backend}/api-keys/{key_id}", headers=headers, timeout=TIMEOUT)
        return r.ok, None if r.ok else f"Error {r.status_code}: {r.text}"
    except requests.ConnectionError:
        return False, "Backend unreachable."


# ─── Users ─────────────────────────────────────────────────────────────────


def register_user(
    backend: str,
    headers: dict,
    username: str,
    password: str,
    role: str,
    allowed_skills: list[str],
) -> tuple[dict | None, str | None]:
    try:
        r = requests.post(
            f"{backend}/auth/register",
            json={
                "username": username,
                "password": password,
                "role": role,
                "allowed_skills": allowed_skills,
            },
            headers=headers,
            timeout=TIMEOUT,
        )
        if r.status_code == 201:
            return r.json(), None
        return None, f"Error {r.status_code}: {r.text}"
    except requests.ConnectionError:
        return None, "Backend unreachable."


def list_users(backend: str, headers: dict) -> tuple[list | None, str | None]:
    try:
        r = requests.get(f"{backend}/auth/users", headers=headers, timeout=TIMEOUT)
        if r.ok:
            return r.json(), None
        return None, f"Error {r.status_code}: {r.text}"
    except requests.ConnectionError:
        return None, "Backend unreachable."


def update_user_permissions(
    backend: str, headers: dict, username: str, allowed_skills: list[str]
) -> tuple[bool, str | None]:
    try:
        r = requests.put(
            f"{backend}/auth/users/{username}/permissions",
            json={"allowed_skills": allowed_skills},
            headers=headers,
            timeout=TIMEOUT,
        )
        return r.ok, None if r.ok else r.text
    except requests.ConnectionError:
        return False, "Backend unreachable."


def delete_user(backend: str, headers: dict, username: str) -> tuple[bool, str | None]:
    try:
        r = requests.delete(f"{backend}/auth/users/{username}", headers=headers, timeout=TIMEOUT)
        return r.ok, None if r.ok else f"Error {r.status_code}: {r.text}"
    except requests.ConnectionError:
        return False, "Backend unreachable."
