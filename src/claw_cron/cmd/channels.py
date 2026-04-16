# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""channels command group — manage message channels."""

from __future__ import annotations

import asyncio
from datetime import datetime

import click
import httpx
from rich.console import Console
from rich.table import Table

from claw_cron.config import load_config, save_config
from claw_cron.contacts import Contact, load_contacts, save_contact
from claw_cron.qqbot import GatewayConfig, QQBotWebSocket
from claw_cron.channels.qqbot import QQBotConfig

console = Console()


@click.group()
def channels() -> None:
    """Manage message channels (QQ Bot, iMessage, etc.).

    Commands:
        add     Add a new channel configuration
        list    List configured channels
        delete  Delete a channel configuration
        capture Connect to capture user openid
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
    help="Connect WebSocket to capture user openid after configuration",
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
        console.print("\n[bold]Step 2: Capture User OpenID[/bold]\n")
        asyncio.run(_capture_qqbot_openid(alias="me"))


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


@channels.command()
@click.option(
    "--channel-type",
    type=click.Choice(["qqbot"], case_sensitive=False),
    default="qqbot",
    help="Channel to capture openid from",
)
@click.option(
    "--alias",
    prompt="Save as contact alias",
    default="me",
    help="Alias name for the captured contact",
)
def capture(channel_type: str, alias: str) -> None:
    """Connect to channel and capture user openid.

    This command starts a WebSocket connection and waits for you
    to send a message to the bot. When received, your openid is
    captured and saved as a contact alias.

    Example:
        claw-cron channels capture --alias my_friend
        # Then send any message to your QQ Bot
    """
    if channel_type == "qqbot":
        asyncio.run(_capture_qqbot_openid(alias))


async def _capture_qqbot_openid(alias: str) -> None:
    """Capture OpenID from QQ Bot WebSocket."""
    from claw_cron.channels.qqbot import QQBotChannel

    # Load config
    config = load_config()
    qq_config = config.get("channels", {}).get("qqbot", {})
    app_id = qq_config.get("app_id")
    client_secret = qq_config.get("client_secret")

    if not app_id or not client_secret:
        console.print("[red]Error: QQ Bot not configured.[/red]")
        console.print("[dim]Run 'claw-cron channels add' first.[/dim]")
        raise SystemExit(1)

    # Get access token
    with console.status("[bold green]Getting access token..."):
        try:
            qqbot_config = QQBotConfig(app_id=app_id, client_secret=client_secret)
            # Create temporary channel instance for token
            channel = QQBotChannel(qqbot_config)
            token = await channel._get_access_token()
            await channel.close()
        except Exception as e:
            console.print(f"[red]Failed to get access token: {e}[/red]")
            raise SystemExit(1)

    # Prepare WebSocket
    gateway_config = GatewayConfig(app_id=app_id, access_token=token)
    ws_client = QQBotWebSocket(gateway_config)

    captured_openid: str | None = None

    async def on_message(message) -> None:
        nonlocal captured_openid
        captured_openid = message.openid
        console.print(f"\n[green]✓ OpenID captured: [bold]{message.openid}[/bold][/green]")
        console.print(f"[dim]Message content: {message.content}[/dim]")

    ws_client.on_c2c_message = on_message

    # Connect and wait
    console.print("\n[bold]Waiting for message...[/bold]")
    console.print("[dim]Send any message to your QQ Bot to capture your openid.[/dim]")
    console.print("[dim]Press Ctrl+C to cancel.[/dim]\n")

    try:
        # Run until openid captured or user cancels
        async def wait_for_capture() -> None:
            while not captured_openid:
                await asyncio.sleep(0.5)

        await asyncio.gather(
            ws_client.connect(),
            wait_for_capture()
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        return
    finally:
        await ws_client.close()

    # Save contact
    if captured_openid:
        contact = Contact(
            openid=captured_openid,
            channel="qqbot",
            alias=alias,
            created=datetime.now().isoformat(),
        )
        save_contact(contact)
        console.print(f"\n[green]✓ Contact saved as '[bold]{alias}[/bold]'[/green]")
        console.print(f"[dim]You can now use 'claw-cron remind --recipient {alias}'[/dim]")


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
