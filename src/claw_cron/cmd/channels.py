# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""channels command group — manage message channels."""

from __future__ import annotations

import click
import httpx
from rich.console import Console
from rich.table import Table

from claw_cron.config import load_config, save_config
from claw_cron.contacts import Contact, load_contacts, save_contact

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


@channels.command()
@click.option(
    "--channel-type",
    type=click.Choice(["qqbot"], case_sensitive=False),
    prompt="Channel type",
    help="Type of channel to configure",
)
@click.option(
    "--app-id",
    prompt="AppID",
    help="QQ Bot AppID from q.qq.com",
)
@click.option(
    "--client-secret",
    prompt=True,
    hide_input=True,
    help="QQ Bot Client Secret",
)
@click.option(
    "--capture-openid",
    is_flag=True,
    default=False,
    help="Connect WebSocket to capture user openid (Phase 2)",
)
def add(channel_type: str, app_id: str, client_secret: str, capture_openid: bool) -> None:
    """Add a new message channel configuration.

    Interactive prompt to configure QQ Bot credentials.
    Credentials are validated before saving.
    """
    channel_type = channel_type.lower()

    # Validate credentials before saving
    with console.status("[bold green]Validating credentials..."):
        try:
            response = httpx.post(
                "https://bots.qq.com/app/getAppAccessToken",
                json={"appId": app_id, "clientSecret": client_secret},
                timeout=10.0,
            )
            data = response.json()
            if data.get("code", 0) != 0:
                raise click.ClickException(
                    f"Validation failed: {data.get('message', 'Unknown error')}"
                )
            console.print("[green]✓ Credentials validated[/green]")
        except httpx.RequestError as e:
            raise click.ClickException(f"Connection failed: {e}") from e

    # Save to config.yaml
    config = load_config()
    if "channels" not in config:
        config["channels"] = {}
    config["channels"][channel_type] = {
        "app_id": app_id,
        "client_secret": client_secret,
        "enabled": True,
    }
    save_config(config)
    console.print(f"[green]✓ Channel '{channel_type}' configured[/green]")

    # Handle capture_openid flag
    if capture_openid:
        console.print("[yellow]Note: OpenID capture requires WebSocket connection (Phase 2)[/yellow]")
        console.print("[dim]Run 'claw-cron channels capture' after Phase 2 implementation[/dim]")


@channels.command("list")
def list_channels() -> None:
    """List configured message channels."""
    config = load_config()
    channels_config = config.get("channels", {})

    if not channels_config:
        console.print("[dim]No channels configured.[/dim]")
        console.print("[dim]Run 'claw-cron channels add' to add one.[/dim]")
        return

    table = Table(title="Configured Channels")
    table.add_column("Channel", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("AppID", style="dim")
    table.add_column("Contacts", style="yellow")

    contacts_data = load_contacts()

    for channel_id, cfg in channels_config.items():
        status = "[green]enabled[/green]" if cfg.get("enabled", True) else "[red]disabled[/red]"
        app_id = cfg.get("app_id", "N/A")
        # Count contacts for this channel
        contact_count = sum(1 for c in contacts_data.values() if c.channel == channel_id)
        app_id_display = f"{app_id[:8]}..." if len(str(app_id)) > 8 else str(app_id)
        table.add_row(channel_id, status, app_id_display, str(contact_count))

    console.print(table)


@channels.command()
@click.argument("channel_type", type=click.Choice(["qqbot"]))
@click.option("--force", is_flag=True, help="Skip confirmation")
def delete(channel_type: str, force: bool) -> None:
    """Delete a channel configuration.

    CHANNEL_TYPE is the channel to delete (e.g., 'qqbot').
    """
    config = load_config()
    channels_config = config.get("channels", {})

    if channel_type not in channels_config:
        console.print(f"[yellow]Channel '{channel_type}' not found.[/yellow]")
        return

    if not force:
        if not click.confirm(f"Delete channel '{channel_type}'?"):
            console.print("[dim]Cancelled.[/dim]")
            return

    del channels_config[channel_type]
    save_config(config)
    console.print(f"[green]Channel '{channel_type}' deleted.[/green]")

    # Warn about contacts
    contacts_data = load_contacts()
    channel_contacts = [c for c in contacts_data.values() if c.channel == channel_type]
    if channel_contacts:
        console.print(f"[yellow]Warning: {len(channel_contacts)} contacts still reference this channel.[/yellow]")
        console.print("[dim]Run 'claw-cron channels contacts list' to see them.[/dim]")


@click.group()
def contacts() -> None:
    """Manage contact aliases."""
    pass


@contacts.command("list")
def list_contacts() -> None:
    """List saved contacts."""
    contact_list = load_contacts()
    if not contact_list:
        console.print("[dim]No contacts saved.[/dim]")
        return

    table = Table(title="Contacts")
    table.add_column("Alias", style="cyan")
    table.add_column("Channel", style="green")
    table.add_column("OpenID", style="dim")
    table.add_column("Created", style="dim")

    for alias, contact in contact_list.items():
        openid_display = (
            f"{contact.openid[:16]}..."
            if len(contact.openid) > 16
            else contact.openid
        )
        table.add_row(
            alias,
            contact.channel,
            openid_display,
            contact.created[:10],  # Just date
        )
    console.print(table)


@contacts.command()
@click.argument("alias")
@click.option("--force", is_flag=True, help="Skip confirmation")
def delete(alias: str, force: bool) -> None:
    """Delete a contact by alias.

    ALIAS is the contact alias to delete.
    """
    contacts_data = load_contacts()
    if alias not in contacts_data:
        console.print(f"[yellow]Contact '{alias}' not found.[/yellow]")
        return

    if not force and not click.confirm(f"Delete contact '{alias}'?"):
        return

    # Load YAML file and remove contact
    from pathlib import Path
    import yaml

    from claw_cron.contacts import CONTACTS_FILE

    contacts_file = CONTACTS_FILE
    if contacts_file.exists():
        with contacts_file.open() as f:
            data = yaml.safe_load(f) or {}
        if "contacts" in data and alias in data["contacts"]:
            del data["contacts"][alias]
            with contacts_file.open("w") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    console.print(f"[green]Contact '{alias}' deleted.[/green]")


# Register contacts as subcommand of channels
channels.add_command(contacts)
