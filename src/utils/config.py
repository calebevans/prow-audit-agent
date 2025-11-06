"""Configuration management for LLM providers and settings."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: str
    api_key: str
    model: str
    base_url: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4000


def get_llm_config() -> LLMConfig:
    """Get LLM configuration from environment variables.

    Returns:
        LLM configuration object

    Raises:
        ValueError: If required environment variables are not set
    """
    provider = os.getenv("LLM_PROVIDER", "openai")
    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        raise ValueError("LLM_API_KEY environment variable must be set")

    model = os.getenv("LLM_MODEL", "gpt-4")
    base_url = os.getenv("LLM_BASE_URL")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4000"))

    return LLMConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def configure_dspy_lm(config: LLMConfig) -> None:
    """Configure DSPy with the specified LLM.

    Args:
        config: LLM configuration

    Raises:
        ValueError: If provider is not supported
    """
    import os

    import dspy

    provider_lower = config.provider.lower()

    is_local_server = config.base_url and (
        "localhost" in config.base_url
        or "127.0.0.1" in config.base_url
        or "host.containers.internal" in config.base_url
    )
    force_basic_mode = os.getenv("LLM_BASIC_MODE", "false").lower() == "true"

    if provider_lower in ["openai", "azure"]:
        if is_local_server or force_basic_mode:
            model_name = (
                config.model.split("/")[-1] if "/" in config.model else config.model
            )

            lm = dspy.LM(
                model=f"openai/{model_name}",
                api_key=config.api_key or "dummy",
                api_base=config.base_url,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                cache=False,
            )
        else:
            lm = dspy.LM(
                model=f"openai/{config.model}",
                api_key=config.api_key,
                api_base=config.base_url,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
    elif provider_lower == "anthropic":
        lm = dspy.LM(
            model=f"anthropic/{config.model}",
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    elif provider_lower == "gemini":
        lm = dspy.LM(
            model=f"gemini/{config.model}",
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    elif provider_lower == "ollama":
        base_url = config.base_url or "http://localhost:11434"
        lm = dspy.LM(
            model=f"ollama/{config.model}",
            api_base=base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    elif provider_lower == "openrouter":
        lm = dspy.LM(
            model=config.model,
            api_key=config.api_key,
            api_base="https://openrouter.ai/api/v1",
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    else:
        lm = dspy.LM(
            model=config.model,
            api_key=config.api_key,
            api_base=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    dspy.configure(lm=lm)
