# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""config command — manage claw-cron configuration."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from claw_cron.channels import CHANNEL_REGISTRY

console = Console()


@click.group()
def config() -> None:
    """Configuration commands."""
    pass


@config.command()
def channels() -> None:
    """List available message channels and their status.

    Shows all registered channels and their configuration status.
    Channels require proper environment variables to be enabled.

    Example:
        claw-cron config channels
    """
    table = Table(title="Available Channels")
    table.add_column("Channel", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Config Required")

    for channel_id in sorted(CHANNEL_REGISTRY.keys()):
        channel_class = CHANNEL_REGISTRY[channel_id]
        try:
            channel = channel_class()
            if hasattr(channel, "config") and channel.config.enabled:
                status = "[green]Enabled[/green]"
            else:
                status = "[yellow]Disabled[/yellow]"
        except Exception:
            status = "[red]Not Configured[/red]"

        # Show config hints based on channel type
        if channel_id == "qqbot":
            config_hint = "QQBOT_APP_ID, QQBOT_CLIENT_SECRET"
        elif channel_id == "imessage":
            config_hint = "None (macOS only)"
        else:
            config_hint = "See documentation"

        table.add_row(channel_id, status, config_hint)

    console.print(table)
