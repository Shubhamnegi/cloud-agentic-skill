"""
Concrete embedding providers implementing the Strategy pattern.
"""
from __future__ import annotations
import logging
import os

from app.core.interfaces import EmbeddingProvider

logger = logging.getLogger(__name__)


class SentenceTransformerProvider(EmbeddingProvider):
    """Local embedding using sentence-transformers.

    On first run the model is downloaded from HuggingFace and saved to
    *cache_dir/<model_name>*.  On subsequent starts the model is loaded
    directly from disk — no internet required, safe for PVCs.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_dir: str = "./models"):
        from sentence_transformers import SentenceTransformer

        # Sanitise model name for use as a directory name (e.g. replace '/')
        safe_name = model_name.replace("/", "__")
        local_path = os.path.join(cache_dir, safe_name)

        if os.path.isdir(local_path):
            logger.info("Loading SentenceTransformer from cache: %s", local_path)
            self._model = SentenceTransformer(local_path)
        else:
            logger.info(
                "Downloading SentenceTransformer model '%s' → %s",
                model_name, local_path,
            )
            os.makedirs(cache_dir, exist_ok=True)
            self._model = SentenceTransformer(model_name)
            self._model.save(local_path)
            logger.info("Model saved to %s", local_path)

        self._dims: int = self._model.get_sentence_embedding_dimension()
        logger.info("Model ready — dimensions: %d", self._dims)

    def encode(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()

    def get_dimensions(self) -> int:
        return self._dims


class OpenAIProvider(EmbeddingProvider):
    """Cloud embedding using the OpenAI API."""

    _DIMS_MAP = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        import openai

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        self._dims = self._DIMS_MAP.get(model, 1536)
        logger.info("OpenAI embedding provider initialised — model: %s", model)

    def encode(self, text: str) -> list[float]:
        response = self._client.embeddings.create(input=text, model=self._model)
        return response.data[0].embedding

    def get_dimensions(self) -> int:
        return self._dims


# ─── Factory ────────────────────────────────────────────────────

def create_embedding_provider(
    model_name: str = "all-MiniLM-L6-v2",
    openai_api_key: str | None = None,
    cache_dir: str = "./models",
) -> EmbeddingProvider:
    """
    Factory that returns the correct provider based on the model name.
    If *model_name* starts with ``text-embedding-``, the OpenAI provider
    is used; otherwise a local SentenceTransformer is loaded from (or
    saved to) *cache_dir*.
    """
    if model_name.startswith("text-embedding-"):
        if not openai_api_key:
            raise ValueError("openai_api_key is required for OpenAI models")
        return OpenAIProvider(api_key=openai_api_key, model=model_name)
    return SentenceTransformerProvider(model_name=model_name, cache_dir=cache_dir)
