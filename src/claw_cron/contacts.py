# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Contact management for claw-cron.

This module provides contact alias management for easier recipient resolution.
Contacts are stored in a YAML file keyed by "channel/alias" so that different
channels can share the same alias name without overwriting each other.

Storage:
    ~/.config/claw-cron/contacts.yaml

Example contacts.yaml:
    contacts:
        qqbot/me:
            openid: ABC123DEF456
            channel: qqbot
            alias: me
            created: "2024-01-01T00:00:00"
        wecom/me:
            openid: XYZ789
            channel: wecom
            alias: me
            created: "2024-01-02T00:00:00"
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

CONTACTS_FILE = Path.home() / ".config" / "claw-cron" / "contacts.yaml"


@dataclass
class Contact:
    """Contact information for a message recipient.

    Attributes:
        openid: Bot-specific user openid.
        channel: Channel type (e.g., "qqbot", "imessage").
        alias: User-friendly name for the contact.
        created: ISO timestamp of creation.
        last_message: ISO timestamp of last message (optional).
    """

    openid: str
    channel: str
    alias: str
    created: str
    last_message: str | None = None


def contact_key(channel: str, alias: str) -> str:
    """Build the composite storage key for a contact.

    Format: ``{channel}/{alias}`` — allows the same alias name
    to exist under different channels.
    """
    return f"{channel}/{alias}"


def load_contacts(path: Path = CONTACTS_FILE) -> dict[str, Contact]:
    """Load contacts from YAML file.

    Args:
        path: Path to contacts.yaml.

    Returns:
        Dict mapping ``channel/alias`` key to Contact.
        Empty dict if file doesn't exist.
    """
    if not path.exists():
        return {}

    with path.open() as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    contacts_data: dict[str, dict[str, Any]] = data.get("contacts", {})
    return {
        key: Contact(**info)
        for key, info in contacts_data.items()
    }


def save_contact(contact: Contact, path: Path = CONTACTS_FILE) -> None:
    """Save or update a contact.

    Creates parent directories if needed. Uses ``channel/alias`` as the
    storage key so that the same alias under a different channel does not
    overwrite an existing one.

    Args:
        contact: Contact to save.
        path: Path to contacts.yaml.
    """
    contacts = load_contacts(path)
    key = contact_key(contact.channel, contact.alias)
    contacts[key] = contact

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump(
            {"contacts": {key: asdict(c) for key, c in contacts.items()}},
            f,
            allow_unicode=True,
            default_flow_style=False,
        )


def resolve_recipient(
    recipient: str,
    channel: str,
    path: Path = CONTACTS_FILE,
) -> str:
    """Resolve recipient alias to openid format.

    - If channel is 'system', return recipient as-is (no resolution needed)
    - If recipient starts with "c2c:" or "group:", return as-is
    - If recipient is a known alias *for the given channel*, return "c2c:{openid}"
    - Raise ValueError if alias not found or channel mismatch

    Args:
        recipient: Recipient identifier (alias or openid format).
        channel: Expected channel type.
        path: Path to contacts.yaml.

    Returns:
        Formatted recipient string (e.g., "c2c:OPENID").

    Raises:
        ValueError: If alias not found or channel mismatch.
    """
    # System channel doesn't need recipient resolution
    if channel == "system":
        return recipient

    # If already in openid format, return as-is
    if recipient.startswith("c2c:") or recipient.startswith("group:"):
        return recipient

    # Try to resolve alias within the specified channel
    contacts = load_contacts(path)
    key = contact_key(channel, recipient)
    if key in contacts:
        return f"c2c:{contacts[key].openid}"

    # Check if the alias exists under a different channel
    matching_channels = [
        c.channel for k, c in contacts.items() if c.alias == recipient
    ]
    if matching_channels:
        raise ValueError(
            f"Contact '{recipient}' channel mismatch: "
            f"expected '{channel}', found under {matching_channels}"
        )

    # Alias not found at all
    available_aliases = [c.alias for c in contacts.values()]
    if available_aliases:
        raise ValueError(
            f"Unknown recipient alias '{recipient}'. Available: {available_aliases}"
        )
    raise ValueError(f"Unknown recipient alias '{recipient}'. No contacts saved.")
