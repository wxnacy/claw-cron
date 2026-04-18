# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for contacts module."""

from datetime import datetime
from pathlib import Path

import pytest

from claw_cron.contacts import Contact, contact_key, load_contacts, save_contact, resolve_recipient


class TestContactKey:
    """Tests for contact_key helper."""

    def test_builds_composite_key(self) -> None:
        """contact_key returns 'channel/alias' format."""
        assert contact_key("qqbot", "me") == "qqbot/me"
        assert contact_key("wecom", "john") == "wecom/john"


class TestLoadContacts:
    """Tests for load_contacts function."""

    def test_returns_empty_dict_when_file_not_exists(self, tmp_path: Path) -> None:
        """load_contacts returns empty dict when file doesn't exist."""
        nonexistent = tmp_path / "contacts.yaml"
        result = load_contacts(nonexistent)
        assert result == {}

    def test_loads_existing_contacts(self, tmp_path: Path) -> None:
        """load_contacts correctly loads existing contacts with composite keys."""
        contacts_file = tmp_path / "contacts.yaml"
        contact = Contact(
            openid="ABC123",
            channel="qqbot",
            alias="me",
            created="2024-01-01T00:00:00",
        )
        save_contact(contact, contacts_file)

        result = load_contacts(contacts_file)
        assert "qqbot/me" in result
        assert result["qqbot/me"].openid == "ABC123"
        assert result["qqbot/me"].alias == "me"


class TestSaveContact:
    """Tests for save_contact function."""

    def test_creates_file_and_parent_dirs(self, tmp_path: Path) -> None:
        """save_contact creates file and parent directories if needed."""
        contacts_file = tmp_path / "subdir" / "contacts.yaml"
        contact = Contact(
            openid="XYZ789",
            channel="qqbot",
            alias="john",
            created=datetime.now().isoformat(),
        )

        save_contact(contact, contacts_file)

        assert contacts_file.exists()

    def test_updates_existing_contact(self, tmp_path: Path) -> None:
        """save_contact updates an existing contact with same channel/alias."""
        contacts_file = tmp_path / "contacts.yaml"
        contact = Contact(
            openid="OLD_ID",
            channel="qqbot",
            alias="me",
            created="2024-01-01T00:00:00",
        )
        save_contact(contact, contacts_file)

        updated = Contact(
            openid="NEW_ID",
            channel="qqbot",
            alias="me",
            created="2024-01-02T00:00:00",
        )
        save_contact(updated, contacts_file)

        result = load_contacts(contacts_file)
        assert result["qqbot/me"].openid == "NEW_ID"

    def test_same_alias_different_channels_no_overwrite(self, tmp_path: Path) -> None:
        """Saving a contact with same alias but different channel does not overwrite."""
        contacts_file = tmp_path / "contacts.yaml"
        qq_contact = Contact(
            openid="QQ_OPENID",
            channel="qqbot",
            alias="me",
            created="2024-01-01T00:00:00",
        )
        save_contact(qq_contact, contacts_file)

        wecom_contact = Contact(
            openid="WECOM_OPENID",
            channel="wecom",
            alias="me",
            created="2024-01-02T00:00:00",
        )
        save_contact(wecom_contact, contacts_file)

        result = load_contacts(contacts_file)
        assert len(result) == 2
        assert result["qqbot/me"].openid == "QQ_OPENID"
        assert result["wecom/me"].openid == "WECOM_OPENID"


class TestResolveRecipient:
    """Tests for resolve_recipient function."""

    def test_returns_c2c_format_as_is(self, tmp_path: Path) -> None:
        """resolve_recipient passes through c2c: prefixed strings."""
        contacts_file = tmp_path / "contacts.yaml"
        result = resolve_recipient("c2c:ABC123", "qqbot", contacts_file)
        assert result == "c2c:ABC123"

    def test_returns_group_format_as_is(self, tmp_path: Path) -> None:
        """resolve_recipient passes through group: prefixed strings."""
        contacts_file = tmp_path / "contacts.yaml"
        result = resolve_recipient("group:XYZ789", "qqbot", contacts_file)
        assert result == "group:XYZ789"

    def test_resolves_known_alias(self, tmp_path: Path) -> None:
        """resolve_recipient resolves known alias within the correct channel."""
        contacts_file = tmp_path / "contacts.yaml"
        contact = Contact(
            openid="ALIAS_OPENID",
            channel="qqbot",
            alias="john",
            created="2024-01-01T00:00:00",
        )
        save_contact(contact, contacts_file)

        result = resolve_recipient("john", "qqbot", contacts_file)
        assert result == "c2c:ALIAS_OPENID"

    def test_raises_value_error_for_unknown_alias(self, tmp_path: Path) -> None:
        """resolve_recipient raises ValueError for unknown alias."""
        contacts_file = tmp_path / "contacts.yaml"
        with pytest.raises(ValueError, match="Unknown recipient alias"):
            resolve_recipient("unknown", "qqbot", contacts_file)

    def test_raises_value_error_for_channel_mismatch(self, tmp_path: Path) -> None:
        """resolve_recipient raises ValueError if alias exists but under a different channel."""
        contacts_file = tmp_path / "contacts.yaml"
        contact = Contact(
            openid="ABC123",
            channel="qqbot",
            alias="me",
            created="2024-01-01T00:00:00",
        )
        save_contact(contact, contacts_file)

        with pytest.raises(ValueError, match="channel mismatch"):
            resolve_recipient("me", "imessage", contacts_file)

    def test_same_alias_different_channels_resolves_correctly(self, tmp_path: Path) -> None:
        """resolve_recipient resolves the correct contact when same alias exists under different channels."""
        contacts_file = tmp_path / "contacts.yaml"
        qq_contact = Contact(
            openid="QQ_ID",
            channel="qqbot",
            alias="me",
            created="2024-01-01T00:00:00",
        )
        save_contact(qq_contact, contacts_file)

        wecom_contact = Contact(
            openid="WECOM_ID",
            channel="wecom",
            alias="me",
            created="2024-01-02T00:00:00",
        )
        save_contact(wecom_contact, contacts_file)

        assert resolve_recipient("me", "qqbot", contacts_file) == "c2c:QQ_ID"
        assert resolve_recipient("me", "wecom", contacts_file) == "c2c:WECOM_ID"
