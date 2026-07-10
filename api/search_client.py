"""Thin client factories for Azure AI Search and Azure OpenAI.

All configuration comes from environment variables (see DESIGN.md / .env.example)
and is read lazily at call time, never at import time, so importing this module
(and api.main) works in environments with no Azure configuration at all.

Missing required settings raise :class:`ConfigurationError`; the API layer
converts that to HTTP 503 with a message naming the missing setting.
"""

import os
from functools import lru_cache

DEFAULT_SEARCH_INDEX = "con-records"
DEFAULT_CHAT_DEPLOYMENT = "gpt-4o-mini"
DEFAULT_EMBEDDING_DEPLOYMENT = "text-embedding-3-small"
DEFAULT_OPENAI_API_VERSION = "2024-06-01"

_AOAI_TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"


class ConfigurationError(RuntimeError):
    """A required environment setting is missing or unusable."""


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"Required setting {name} is not configured; "
            f"set the {name} environment variable (see .env.example)."
        )
    return value


def search_index_name() -> str:
    return os.environ.get("SEARCH_INDEX", "").strip() or DEFAULT_SEARCH_INDEX


def _search_credential():
    key = os.environ.get("SEARCH_API_KEY", "").strip()
    if key:
        from azure.core.credentials import AzureKeyCredential

        return AzureKeyCredential(key)
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()


def get_search_client():
    """SearchClient for the con-records index (SEARCH_* env vars)."""
    from azure.search.documents import SearchClient

    endpoint = _require_env("SEARCH_ENDPOINT")
    return SearchClient(
        endpoint=endpoint,
        index_name=search_index_name(),
        credential=_search_credential(),
    )


def get_search_index_client():
    """SearchIndexClient for index management (used by api.search_sync)."""
    from azure.search.documents.indexes import SearchIndexClient

    endpoint = _require_env("SEARCH_ENDPOINT")
    return SearchIndexClient(endpoint=endpoint, credential=_search_credential())


def openai_configured() -> bool:
    """True when Azure OpenAI looks configured (endpoint present)."""
    return bool(os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip())


def get_openai_client():
    """AzureOpenAI client (AZURE_OPENAI_* env vars; API key or Entra token)."""
    from openai import AzureOpenAI

    endpoint = _require_env("AZURE_OPENAI_ENDPOINT")
    api_version = (
        os.environ.get("AZURE_OPENAI_API_VERSION", "").strip() or DEFAULT_OPENAI_API_VERSION
    )
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    if api_key:
        return AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version=api_version)
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    token_provider = get_bearer_token_provider(DefaultAzureCredential(), _AOAI_TOKEN_SCOPE)
    return AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version=api_version,
    )


def chat_deployment() -> str:
    return os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "").strip() or DEFAULT_CHAT_DEPLOYMENT


def embedding_deployment() -> str:
    return (
        os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "").strip()
        or DEFAULT_EMBEDDING_DEPLOYMENT
    )


@lru_cache(maxsize=1)
def _cached_openai_client():
    return get_openai_client()


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with the configured Azure OpenAI deployment.

    Raises ConfigurationError when AZURE_OPENAI_ENDPOINT is not set.
    """
    if not texts:
        return []
    client = _cached_openai_client()
    response = client.embeddings.create(model=embedding_deployment(), input=list(texts))
    ordered = sorted(response.data, key=lambda item: item.index)
    return [item.embedding for item in ordered]
