# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Global configuration loader for claw-cron."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings

CONFIG_FILE = Path.home() / ".config" / "claw-cron" / "config.yaml"

# Provider-specific default models
PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "claude": "claude-3-5-haiku-20241022",
    "openai": "gpt-4o-mini",
}

# Built-in default client command templates ({prompt} is the placeholder)
_BUILTIN_CLIENTS: dict[str, str] = {
    "kiro-cli": 'kiro-cli -a --no-interactive "{prompt}"',
    "codebuddy": 'codebuddy -y -p "{prompt}"',
    "opencode": 'opencode run --dangerously-skip-permissions "{prompt}"',
}


def load_config(path: Path = CONFIG_FILE) -> dict[str, Any]:
    """Load global config from YAML file.

    Args:
        path: Path to config.yaml.

    Returns:
        Config dict. Empty dict if file doesn't exist.
    """
    if not path.exists():
        return {}
    with path.open() as f:
        return yaml.safe_load(f) or {}


def get_client_cmd(client: str, path: Path = CONFIG_FILE) -> str:
    """Resolve the command template for an AI client.

    Priority: config.yaml > built-in defaults.

    Args:
        client: Client name (e.g., "kiro-cli", "codebuddy", "opencode").
        path: Path to config.yaml.

    Returns:
        Command template string with {prompt} placeholder.

    Raises:
        ValueError: If client is unknown and not in config.yaml.
    """
    cfg = load_config(path)
    clients_cfg: dict[str, str] = cfg.get("clients", {})
    if client in clients_cfg:
        return clients_cfg[client]
    if client in _BUILTIN_CLIENTS:
        return _BUILTIN_CLIENTS[client]
    raise ValueError(f"Unknown AI client: {client!r}. Supported: {list(_BUILTIN_CLIENTS)}")


class AIConfig(BaseSettings):
    """AI provider configuration with environment variable support.

    Environment variables use CLAW_CRON_ prefix:
        - CLAW_CRON_PROVIDER: AI provider ('claude' or 'openai')
        - CLAW_CRON_API_KEY: API key for the provider
        - CLAW_CRON_MODEL: Model name (optional, uses provider default if not set)
        - CLAW_CRON_BASE_URL: Custom API endpoint (optional)

    Attributes:
        provider: AI provider name ('claude' or 'openai').
        model: Model name (provider-specific default if not set).
        api_key: API key for authentication.
        base_url: Custom API base URL (for proxies or local models).
    """

    provider: str = Field(
        default="claude",
        description="AI provider: 'claude' or 'openai'",
    )
    model: str | None = Field(
        default=None,
        description="Model name (provider-specific default if not set)",
    )
    api_key: str | None = Field(
        default=None,
        description="API key (from env var if not set)",
    )
    base_url: str | None = Field(
        default=None,
        description="Custom API base URL (for proxies or local models)",
    )

    class Config:
        env_prefix = "CLAW_CRON_"
        env_file = ".env"
        extra = "ignore"

    def get_effective_model(self) -> str:
        """Get model name with provider-specific default.

        Returns:
            Model name if set, otherwise the default for the current provider.
        """
        if self.model:
            return self.model
        return PROVIDER_DEFAULT_MODELS.get(self.provider, PROVIDER_DEFAULT_MODELS["claude"])


def load_ai_config(config_path: Path | None = None) -> AIConfig:
    """Load AI config from YAML file with environment variable overrides.

    Priority: env vars > config.yaml > defaults

    Args:
        config_path: Path to config.yaml. Defaults to CONFIG_FILE.

    Returns:
        AIConfig instance with loaded settings.
    """
    config_path = config_path or CONFIG_FILE
    cfg = load_config(config_path)

    # Extract AI config section if present
    ai_cfg: dict[str, Any] = cfg.get("ai", {})

    # Create AIConfig with env var overrides (handled by pydantic-settings)
    return AIConfig(**ai_cfg)
