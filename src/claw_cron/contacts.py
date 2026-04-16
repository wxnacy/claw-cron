# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Contact management for claw-cron.

This module provides contact alias management for easier recipient resolution.
Contacts are stored in a YAML file with aliases that can be used in the remind
command instead of raw openids.

Storage:
    ~/.config/claw-cron/contacts.yaml

Example contacts.yaml:
    contacts:
        me:
            openid: ABC123DEF456
            channel: qqbot
            alias: me
            created: "2024-01-01T00:00:00"
        john:
            openid: XYZ789
            channel: qqbot
            alias: john
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


def load_contacts(path: Path = CONTACTS_FILE) -> dict[str, Contact]:
    """Load contacts from YAML file.

    Args:
        path: Path to contacts.yaml.

    Returns:
        Dict mapping alias to Contact. Empty dict if file doesn't exist.
    """
    if not path.exists():
        return {}

    with path.open() as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    contacts_data: dict[str, dict[str, Any]] = data.get("contacts", {})
    return {
        alias: Contact(**info)
        for alias, info in contacts_data.items()
    }


def save_contact(contact: Contact, path: Path = CONTACTS_FILE) -> None:
    """Save or update a contact.

    Creates parent directories if needed. Updates existing contact with
    same alias.

    Args:
        contact: Contact to save.
        path: Path to contacts.yaml.
    """
    contacts = load_contacts(path)
    contacts[contact.alias] = contact

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump(
            {"contacts": {alias: asdict(c) for alias, c in contacts.items()}},
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

    - If recipient starts with "c2c:" or "group:", return as-is
    - If recipient is a known alias, return "c2c:{openid}"
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
    # If already in openid format, return as-is
    if recipient.startswith("c2c:") or recipient.startswith("group:"):
        return recipient

    # Try to resolve alias
    contacts = load_contacts(path)
    if recipient in contacts:
        contact = contacts[recipient]
        if contact.channel != channel:
            raise ValueError(
                f"Contact '{recipient}' channel mismatch: "
                f"expected '{channel}', got '{contact.channel}'"
            )
        return f"c2c:{contact.openid}"

    # Alias not found
    available = list(contacts.keys())
    if available:
        raise ValueError(
            f"Unknown recipient alias '{recipient}'. Available: {available}"
        )
    raise ValueError(f"Unknown recipient alias '{recipient}'. No contacts saved.")
