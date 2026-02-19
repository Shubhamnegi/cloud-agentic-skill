"""
Seed script — populates the Elasticsearch index with sample skills.

Usage:
    python -m scripts.seed_data
"""
from __future__ import annotations

import sys
import os

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opensearchpy import OpenSearch
from app.core.config import get_settings
from app.providers.embedding import create_embedding_provider
from app.repositories.elasticsearch import ElasticsearchSkillRepository


SAMPLE_SKILLS = [
    # ── SQL top-level ─────────────────────────────────────────
    {
        "skill_id": "SQL_SKILL",
        "summary": "SQL database management, migration, and optimization skills.",
        "is_folder": True,
        "sub_skills": ["SQL_SKILL_MIGRATION", "SQL_SKILL_OPTIMIZATION"],
        "instruction": (
            "This is the top-level SQL skill collection. "
            "Navigate to the sub-skills for specific instructions:\n"
            "- **SQL_SKILL_MIGRATION** — Sharding, partitioning, schema changes\n"
            "- **SQL_SKILL_OPTIMIZATION** — Query tuning, indexing strategies"
        ),
    },
    {
        "skill_id": "SQL_SKILL_MIGRATION",
        "summary": "Database migration including sharding, partitioning, and schema changes.",
        "is_folder": False,
        "sub_skills": [],
        "instruction": (
            "# SQL Migration Guide\n\n"
            "## 1. Sharding Strategy\n"
            "- Identify your partition key (e.g., tenant_id, date).\n"
            "- Choose **horizontal** sharding for row distribution or "
            "**vertical** sharding for column separation.\n\n"
            "## 2. Partitioning\n"
            "```sql\n"
            "CREATE TABLE orders (\n"
            "    id BIGINT,\n"
            "    created_at DATE,\n"
            "    amount DECIMAL(10,2)\n"
            ") PARTITION BY RANGE (created_at);\n"
            "```\n\n"
            "## 3. Schema Migrations\n"
            "- Use **Alembic** or **Flyway** for versioned migrations.\n"
            "- Always run migrations in a transaction when possible.\n"
            "- Test rollback scripts before deploying to production."
        ),
    },
    {
        "skill_id": "SQL_SKILL_OPTIMIZATION",
        "summary": "SQL query tuning, indexing strategies, and performance optimization.",
        "is_folder": False,
        "sub_skills": [],
        "instruction": (
            "# SQL Optimization Guide\n\n"
            "## 1. Indexing\n"
            "- Add composite indexes for frequent WHERE + ORDER BY patterns.\n"
            "- Use partial indexes to skip NULL or low-cardinality values.\n\n"
            "## 2. Query Tuning\n"
            "- Run `EXPLAIN ANALYZE` to understand execution plans.\n"
            "- Replace correlated sub-queries with JOINs.\n"
            "- Prefer `EXISTS` over `IN` for large sub-queries.\n\n"
            "## 3. Connection Pooling\n"
            "- Use **PgBouncer** or built-in pool settings.\n"
            "- Keep pool size = (CPU cores × 2) + effective_spindle_count."
        ),
    },
    # ── Python top-level ──────────────────────────────────────
    {
        "skill_id": "PYTHON_SKILL",
        "summary": "Python programming skills for backend development.",
        "is_folder": True,
        "sub_skills": ["PYTHON_SKILL_ASYNC", "PYTHON_SKILL_TESTING"],
        "instruction": (
            "This is the top-level Python skill collection.\n"
            "- **PYTHON_SKILL_ASYNC** — asyncio, concurrency patterns\n"
            "- **PYTHON_SKILL_TESTING** — pytest, mocking, coverage"
        ),
    },
    {
        "skill_id": "PYTHON_SKILL_ASYNC",
        "summary": "Python async programming with asyncio — concurrency patterns and best practices.",
        "is_folder": False,
        "sub_skills": [],
        "instruction": (
            "# Python Async Guide\n\n"
            "## 1. Core Concepts\n"
            "- **Coroutine:** A function defined with `async def`.\n"
            "- **Event Loop:** The scheduler that runs coroutines.\n"
            "- **await:** Yields control back to the event loop.\n\n"
            "## 2. Patterns\n"
            "```python\n"
            "import asyncio\n\n"
            "async def fetch(url):\n"
            "    async with aiohttp.ClientSession() as session:\n"
            "        async with session.get(url) as resp:\n"
            "            return await resp.text()\n\n"
            "# Run multiple requests concurrently\n"
            "results = await asyncio.gather(\n"
            "    fetch('https://api.example.com/a'),\n"
            "    fetch('https://api.example.com/b'),\n"
            ")\n"
            "```\n\n"
            "## 3. Best Practices\n"
            "- Never mix `asyncio.run()` with a running event loop.\n"
            "- Use `asyncio.TaskGroup` (Python 3.11+) for structured concurrency.\n"
            "- Prefer async context managers for resource cleanup."
        ),
    },
    {
        "skill_id": "PYTHON_SKILL_TESTING",
        "summary": "Python testing with pytest — unit tests, mocking, and code coverage.",
        "is_folder": False,
        "sub_skills": [],
        "instruction": (
            "# Python Testing Guide\n\n"
            "## 1. pytest Basics\n"
            "```bash\n"
            "pip install pytest pytest-cov\n"
            "pytest --cov=app tests/\n"
            "```\n\n"
            "## 2. Fixtures\n"
            "```python\n"
            "import pytest\n\n"
            "@pytest.fixture\n"
            "def db_connection():\n"
            "    conn = create_connection()\n"
            "    yield conn\n"
            "    conn.close()\n"
            "```\n\n"
            "## 3. Mocking\n"
            "```python\n"
            "from unittest.mock import patch\n\n"
            "@patch('app.services.external_api.call')\n"
            "def test_service(mock_call):\n"
            "    mock_call.return_value = {'status': 'ok'}\n"
            "    result = my_service()\n"
            "    assert result['status'] == 'ok'\n"
            "```"
        ),
    },
    # ── DevOps ────────────────────────────────────────────────
    {
        "skill_id": "DEVOPS_SKILL",
        "summary": "DevOps skills — CI/CD, containerization, monitoring, and infrastructure.",
        "is_folder": True,
        "sub_skills": ["DEVOPS_SKILL_DOCKER", "DEVOPS_SKILL_CICD"],
        "instruction": (
            "Top-level DevOps skill collection.\n"
            "- **DEVOPS_SKILL_DOCKER** — Dockerfile best practices, multi-stage builds\n"
            "- **DEVOPS_SKILL_CICD** — GitHub Actions, GitLab CI pipelines"
        ),
    },
    {
        "skill_id": "DEVOPS_SKILL_DOCKER",
        "summary": "Docker containerization — Dockerfile best practices and multi-stage builds.",
        "is_folder": False,
        "sub_skills": [],
        "instruction": (
            "# Docker Best Practices\n\n"
            "## 1. Multi-Stage Builds\n"
            "```dockerfile\n"
            "FROM python:3.12 AS builder\n"
            "COPY requirements.txt .\n"
            "RUN pip install --prefix=/install -r requirements.txt\n\n"
            "FROM python:3.12-slim\n"
            "COPY --from=builder /install /usr/local\n"
            "COPY app/ app/\n"
            "CMD [\"uvicorn\", \"app.main:app\"]\n"
            "```\n\n"
            "## 2. Layer Caching\n"
            "- Copy dependency files before source code.\n"
            "- Use `.dockerignore` to exclude `.git`, `node_modules`.\n\n"
            "## 3. Security\n"
            "- Run as non-root: `USER 1000`.\n"
            "- Scan images with `trivy` or `grype`."
        ),
    },
    {
        "skill_id": "DEVOPS_SKILL_CICD",
        "summary": "CI/CD pipelines with GitHub Actions and GitLab CI.",
        "is_folder": False,
        "sub_skills": [],
        "instruction": (
            "# CI/CD Pipeline Guide\n\n"
            "## GitHub Actions Example\n"
            "```yaml\n"
            "name: CI\n"
            "on: [push, pull_request]\n"
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: actions/setup-python@v5\n"
            "        with: { python-version: '3.12' }\n"
            "      - run: pip install -r requirements.txt\n"
            "      - run: pytest --cov\n"
            "```\n\n"
            "## Best Practices\n"
            "- Cache dependencies between runs.\n"
            "- Run linting and tests in parallel jobs.\n"
            "- Use environment protection rules for production deploys."
        ),
    },
]


def main():
    settings = get_settings()
    print(f"Connecting to OpenSearch at {settings.elasticsearch_url} …")

    use_ssl = settings.elasticsearch_url.startswith("https")
    http_auth = (
        (settings.elasticsearch_username, settings.elasticsearch_password)
        if settings.elasticsearch_username
        else None
    )
    client_kwargs: dict = dict(
        hosts=[settings.elasticsearch_url],
        use_ssl=use_ssl,
        verify_certs=settings.elasticsearch_verify_certs if use_ssl else False,
        ssl_show_warn=False,
        request_timeout=30,
    )
    if http_auth:
        client_kwargs["http_auth"] = http_auth

    es = OpenSearch(**client_kwargs)
    if not es.ping():
        print("ERROR: OpenSearch is not reachable.")
        sys.exit(1)

    embedding = create_embedding_provider(settings.embedding_model)
    repo = ElasticsearchSkillRepository(es, index=settings.elasticsearch_index, dims=embedding.get_dimensions())
    repo.ensure_index()

    print(f"Seeding {len(SAMPLE_SKILLS)} skills into '{settings.elasticsearch_index}' …")
    for skill in SAMPLE_SKILLS:
        vector = embedding.encode(skill["summary"])
        doc = {**skill, "skill_desc_vector": vector}
        repo.upsert(doc)
        print(f"  ✓ {skill['skill_id']}")

    print("Done!")


if __name__ == "__main__":
    main()
