"""
Dependency-Injection container.

Initialises all concrete implementations once at startup and
exposes them via FastAPI ``Depends()`` callables.
"""
from __future__ import annotations

import logging
import time
from typing import Generator

from opensearchpy import OpenSearch
from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.models import TokenPayload
from app.mcp.router import MCPToolRouter
from app.providers.embedding import create_embedding_provider
from app.repositories.elasticsearch import (
    ElasticsearchAPIKeyRepository,
    ElasticsearchSkillRepository,
    ElasticsearchUserRepository,
)
from app.services.api_keys import APIKeyService
from app.services.auth import AuthService
from app.services.orchestrator import SkillOrchestrator

logger = logging.getLogger(__name__)

# ── Singletons (populated by ``init_services``) ──────────────

_es_client: OpenSearch | None = None
_orchestrator: SkillOrchestrator | None = None
_auth_service: AuthService | None = None
_api_key_service: APIKeyService | None = None
_mcp_router: MCPToolRouter | None = None


def _build_os_client(settings: Settings, *, probe: bool = False) -> OpenSearch:
    """Create an OpenSearch client with optional basic auth and TLS."""
    http_auth = (
        (settings.elasticsearch_username, settings.elasticsearch_password)
        if settings.elasticsearch_username
        else None
    )
    use_ssl = settings.elasticsearch_url.startswith("https")
    kwargs: dict = dict(
        hosts=[settings.elasticsearch_url],
        use_ssl=use_ssl,
        verify_certs=settings.elasticsearch_verify_certs if use_ssl else False,
        ssl_show_warn=False,
        request_timeout=min(settings.elasticsearch_timeout, 10) if probe else settings.elasticsearch_timeout,
        max_retries=0,
        retry_on_timeout=False,
    )
    if http_auth:
        kwargs["http_auth"] = http_auth
    return OpenSearch(**kwargs)


def _wait_for_es(settings: Settings) -> OpenSearch:
    """Block until OpenSearch is reachable, with exponential back-off.

    A *temporary* client is used for the readiness loop so that failed
    pings don't pile up in the urllib3 connection pool (avoids
    ``FullPoolError``).  Once reachable a *production* client is returned.
    """
    probe = _build_os_client(settings, probe=True)

    retries = 30
    delay = 2.0
    max_delay = 30.0
    for attempt in range(1, retries + 1):
        try:
            if probe.ping():
                logger.info("OpenSearch reachable at %s", settings.elasticsearch_url)
                break
        except Exception as exc:
            logger.warning("OpenSearch ping error (attempt %d/%d): %s", attempt, retries, exc)
        logger.warning("OpenSearch not ready (attempt %d/%d) — retrying in %.1fs …", attempt, retries, delay)
        time.sleep(delay)
        delay = min(delay * 1.5, max_delay)
    else:
        probe.close()
        raise RuntimeError(
            f"OpenSearch at {settings.elasticsearch_url} not reachable after {retries} attempts"
        )

    probe.close()
    return _build_os_client(settings, probe=False)


def init_services(settings: Settings | None = None) -> None:
    """Wire up all services. Called once during the FastAPI lifespan."""
    global _es_client, _orchestrator, _auth_service, _api_key_service, _mcp_router

    settings = settings or get_settings()
    logger.info("Initialising services — ES=%s  model=%s", settings.elasticsearch_url, settings.embedding_model)

    # 1. Elasticsearch client
    _es_client = _wait_for_es(settings)

    # 2. Repositories
    embedding = create_embedding_provider(
        settings.embedding_model,
        cache_dir=settings.model_cache_dir,
    )
    skill_repo = ElasticsearchSkillRepository(
        _es_client, index=settings.elasticsearch_index, dims=embedding.get_dimensions()
    )
    user_repo = ElasticsearchUserRepository(_es_client, index=settings.elasticsearch_user_index)
    key_repo = ElasticsearchAPIKeyRepository(_es_client, index=settings.elasticsearch_api_key_index)

    # 3. Ensure indices
    skill_repo.ensure_index()
    user_repo.ensure_index()
    key_repo.ensure_index()

    # 4. Services
    _orchestrator = SkillOrchestrator(embedding, skill_repo)
    _auth_service = AuthService(user_repo, skill_repo, settings)
    _api_key_service = APIKeyService(key_repo)

    # 5. MCP
    _mcp_router = MCPToolRouter(_orchestrator)

    # 6. Default admin
    _auth_service.ensure_default_admin(settings)
    logger.info("Services initialised.")


# ── FastAPI Depends helpers ───────────────────────────────────

def get_orchestrator() -> SkillOrchestrator:
    assert _orchestrator is not None, "Services not initialised"
    return _orchestrator


def get_auth() -> AuthService:
    assert _auth_service is not None, "Services not initialised"
    return _auth_service


def get_api_key_service() -> APIKeyService:
    assert _api_key_service is not None, "Services not initialised"
    return _api_key_service


def get_mcp_router() -> MCPToolRouter:
    assert _mcp_router is not None, "Services not initialised"
    return _mcp_router


# ── Auth dependencies ─────────────────────────────────────────

def require_token(
    authorization: str = Header(..., alias="Authorization"),
    auth: AuthService = Depends(get_auth),
) -> TokenPayload:
    """Validate a Bearer JWT and return the decoded payload."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ")
    payload = auth.decode_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


def require_admin(payload: TokenPayload = Depends(require_token)) -> TokenPayload:
    """Require an admin-role JWT."""
    if payload.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return payload


def require_api_key(
    x_api_key: str = Header(...),
    svc: APIKeyService = Depends(get_api_key_service),
) -> dict:
    """Validate an MCP API key."""
    key_doc = svc.validate_key(x_api_key)
    if key_doc is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return key_doc
