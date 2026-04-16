# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""channels command group — manage message channels."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.group()
def channels() -> None:
    """Manage message channels (QQ Bot, iMessage, etc.).

    Commands:
        add     Add a new channel configuration
        list    List configured channels
        delete  Delete a channel configuration
        contacts Manage contact aliases
    """
    pass


# Placeholder subcommands - will be implemented in subsequent tasks
@channels.command()
def add() -> None:
    """Add a new message channel configuration.

    Interactive prompt to configure QQ Bot credentials.
    Credentials are validated before saving.
    """
    console.print("[yellow]Coming soon: Interactive channel configuration[/yellow]")
    console.print("[dim]Use --help for available options[/dim]")


@channels.command("list")
def list_channels() -> None:
    """List configured message channels."""
    console.print("[dim]No channels configured.[/dim]")
    console.print("[dim]Run 'claw-cron channels add' to add one.[/dim]")


@channels.command()
@click.argument("channel_type", type=click.Choice(["qqbot"]))
@click.option("--force", is_flag=True, help="Skip confirmation")
def delete(channel_type: str, force: bool) -> None:
    """Delete a channel configuration.

    CHANNEL_TYPE is the channel to delete (e.g., 'qqbot').
    """
    console.print(f"[yellow]Channel '{channel_type}' not found.[/yellow]")


@click.group()
def contacts() -> None:
    """Manage contact aliases."""
    pass


@contacts.command("list")
def list_contacts() -> None:
    """List saved contacts."""
    console.print("[dim]No contacts saved.[/dim]")


# Register contacts as subcommand of channels
channels.add_command(contacts)
