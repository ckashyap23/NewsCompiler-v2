"""LLM provider selection for OpenAI and Azure OpenAI."""

import os
from dataclasses import dataclass
from typing import Literal


ProviderName = Literal["openai", "azure_openai"]


@dataclass(frozen=True)
class LLMConfig:
    provider: ProviderName
    model: str
    client: object


def get_llm_provider() -> ProviderName:
    provider = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
    if provider in {"azure", "azure_openai", "azure-openai"}:
        return "azure_openai"
    if provider == "openai":
        return "openai"
    raise ValueError("LLM_PROVIDER must be either 'openai' or 'azure_openai'")


def get_llm_config(operation: str, default_openai_model: str) -> LLMConfig:
    """Build the configured LLM client/model for an operation."""
    provider = get_llm_provider()

    try:
        from openai import AzureOpenAI, OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The `openai` package is required. Install it with `pip install openai`."
        ) from exc

    if provider == "openai":
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in the environment")

        model = _openai_model_for_operation(operation, default_openai_model)
        return LLMConfig(provider=provider, model=model, client=OpenAI(api_key=api_key))

    endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()
    api_key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
    api_version = (os.getenv("AZURE_OPENAI_API_VERSION") or "").strip()
    deployment = _azure_deployment_for_operation(operation)

    missing = []
    if not endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not api_key:
        missing.append("AZURE_OPENAI_API_KEY")
    if not api_version:
        missing.append("AZURE_OPENAI_API_VERSION")
    if not deployment:
        missing.append("AZURE_OPENAI_DEPLOYMENT")
    if missing:
        raise RuntimeError(f"{', '.join(missing)} must be set when LLM_PROVIDER=azure_openai")

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )
    return LLMConfig(provider=provider, model=deployment, client=client)


def _openai_model_for_operation(operation: str, default_openai_model: str) -> str:
    if operation == "topic_research":
        return (os.getenv("OPENAI_TOPIC_MODEL") or default_openai_model).strip()
    if operation == "newsletter_compile":
        return (os.getenv("OPENAI_NEWSLETTER_MODEL") or default_openai_model).strip()
    return default_openai_model


def _azure_deployment_for_operation(operation: str) -> str:
    if operation == "topic_research":
        return (
            os.getenv("AZURE_OPENAI_TOPIC_DEPLOYMENT")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT")
            or ""
        ).strip()
    if operation == "newsletter_compile":
        return (
            os.getenv("AZURE_OPENAI_NEWSLETTER_DEPLOYMENT")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT")
            or ""
        ).strip()
    return (os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip()
