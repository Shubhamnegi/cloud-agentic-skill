"""
Configuration module using pydantic-settings.
All settings are loaded from environment variables or a .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # App
    app_name: str = "Cloud Agentic Skill Manager"
    debug: bool = False

    # OpenSearch / Elasticsearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_username: str = ""
    elasticsearch_password: str = ""
    elasticsearch_verify_certs: bool = True
    elasticsearch_index: str = "agent_skills"
    elasticsearch_user_index: str = "skill_users"
    elasticsearch_api_key_index: str = "skill_api_keys"
    elasticsearch_timeout: int = 30
    elasticsearch_max_retries: int = 5
    elasticsearch_retry_on_timeout: bool = True

    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dims: int = 384
    # Directory where the model is saved locally (mount a PVC here in K8s)
    model_cache_dir: str = "./models"

    # Security
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60
    default_admin_username: str = "admin"
    default_admin_password: str = "admin"

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Dashboard
    backend_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
