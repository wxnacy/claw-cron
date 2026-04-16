# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Global configuration loader for claw-cron."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_FILE = Path.home() / ".config" / "claw-cron" / "config.yaml"

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
