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
from claw_cron.prompt import prompt_confirm, prompt_channel_select, prompt_capture_channel_select
from claw_cron.channels import CHANNEL_REGISTRY, get_channel_status

console = Console()

CHANNEL_DISPLAY_NAMES = {
    "qqbot": "QQ Bot",
    "feishu": "飞书",
    "wecom": "企业微信",
}


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
def add() -> None:
    """Add a new message channel configuration.

    Interactive prompt to configure message channel credentials.
    Channel type is selected from an interactive list with status display.
    Credentials are validated before saving.
    """
    # Interactive channel selection
    channel_type = prompt_channel_select()
    channel_type = channel_type.lower()

    # Check if already configured and prompt for overwrite
    config = load_config()
    channels_config = config.get("channels", {})

    if channel_type in channels_config:
        if not prompt_confirm(f"通道 '{channel_type}' 已配置，是否覆盖?"):
            console.print("[dim]已取消[/dim]")
            return

    def _do_capture(ch_type: str) -> None:
        from claw_cron.channels import get_channel
        from claw_cron.channels.exceptions import ChannelConfigError, ChannelError
        display_name = CHANNEL_DISPLAY_NAMES.get(ch_type, ch_type)
        ch = get_channel(ch_type)
        console.print(f"\n[dim]请向你的 {display_name} 机器人发送任意消息[/dim]")
        console.print("[dim]按 Ctrl+C 取消[/dim]\n")
        try:
            with console.status(f"[bold green]等待来自 {display_name} 的消息..."):
                openid = asyncio.run(ch.capture_openid())
            console.print(f"[green]✓ OpenID 已捕获: [bold]{openid}[/bold][/green]")
            save_contact(Contact(openid=openid, channel=ch_type, alias="me", created=datetime.now().isoformat()))
            console.print("[green]✓ 联系人已保存为 'me'[/green]")
        except KeyboardInterrupt:
            console.print("\n[yellow]已取消[/yellow]")
        except ChannelError as e:
            if "timed out" in str(e).lower():
                console.print(f"\n[red]✗ Capture 超时（5 分钟），请确认机器人在线后重试[/red]")
            else:
                console.print(f"[red]Capture 失败: {e}[/red]")
        except ChannelConfigError as e:
            console.print(f"[red]Capture 失败: {e}[/red]")

    # Channel-specific configuration flow
    if channel_type == "qqbot":
        app_id = click.prompt("AppID", type=str)
        client_secret = click.prompt("Client Secret", type=str, hide_input=True)

        # Validate credentials before saving
        with console.status("[bold green]正在验证凭证..."):
            try:
                response = httpx.post(
                    "https://bots.qq.com/app/getAppAccessToken",
                    json={"appId": app_id, "clientSecret": client_secret},
                    timeout=10.0,
                )
                data = response.json()
                if data.get("code", 0) != 0:
                    raise click.ClickException(
                        f"验证失败: {data.get('message', '未知错误')}"
                    )
                console.print("[green]✓ 凭证验证成功[/green]")
            except httpx.RequestError as e:
                raise click.ClickException(f"连接失败: {e}") from e

        # Save to config.yaml
        if "channels" not in config:
            config["channels"] = {}
        config["channels"][channel_type] = {
            "app_id": app_id,
            "client_secret": client_secret,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }
        save_config(config)
        console.print(f"[green]✓ 通道 '{channel_type}' 配置完成[/green]")

        if prompt_confirm("是否立即获取用户 ID (capture)?"):
            _do_capture("qqbot")

    elif channel_type == "feishu":
        app_id = click.prompt("App ID", type=str)
        app_secret = click.prompt("App Secret", type=str, hide_input=True)

        # Validate credentials before saving (per D-08)
        with console.status("[bold green]正在验证凭证..."):
            try:
                response = httpx.post(
                    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                    json={"app_id": app_id, "app_secret": app_secret},
                    timeout=10.0,
                )
                data = response.json()
                if data.get("code", 0) != 0:
                    raise click.ClickException(
                        f"验证失败: {data.get('message', '未知错误')}"
                    )
                console.print("[green]✓ 凭证验证成功[/green]")
            except httpx.RequestError as e:
                raise click.ClickException(f"连接失败: {e}") from e

        # Save to config.yaml
        if "channels" not in config:
            config["channels"] = {}
        config["channels"][channel_type] = {
            "app_id": app_id,
            "app_secret": app_secret,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }
        save_config(config)
        console.print(f"[green]✓ 通道 '{channel_type}' 配置完成[/green]")

        if prompt_confirm("是否立即获取用户 ID (capture)?"):
            _do_capture("feishu")

    elif channel_type == "email":
        host = click.prompt("SMTP Host", type=str)
        port = click.prompt("SMTP Port", type=int, default=587)
        username = click.prompt("Username", type=str)
        password = click.prompt("Password", type=str, hide_input=True)
        from_email = click.prompt("From Email", type=str)
        use_tls = click.confirm("Use TLS", default=True)

        # Validate by sending a test email (D-05)
        with console.status("[bold green]正在发送验证邮件..."):
            try:
                import asyncio as _asyncio
                from claw_cron.channels.email import EmailChannel, EmailConfig
                test_config = EmailConfig(
                    host=host, port=port, username=username,
                    password=password, from_email=from_email, use_tls=use_tls,
                )
                channel = EmailChannel(test_config)
                result = _asyncio.run(channel.send_text(
                    from_email,
                    "claw-cron 邮件通道验证邮件\n\n此邮件由 claw-cron 自动发送，用于验证 SMTP 配置。",
                ))
                if not result.success:
                    raise click.ClickException(f"验证失败: {result.error}")
                console.print("[green]✓ 验证邮件已发送[/green]")
            except Exception as e:
                if isinstance(e, click.ClickException):
                    raise
                raise click.ClickException(f"连接失败: {e}") from e

        # Save to config.yaml
        if "channels" not in config:
            config["channels"] = {}
        config["channels"][channel_type] = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "from_email": from_email,
            "use_tls": use_tls,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }
        save_config(config)
        console.print(f"[green]✓ 通道 '{channel_type}' 配置完成[/green]")

    elif channel_type == "imessage":
        # iMessage doesn't require credentials
        if "channels" not in config:
            config["channels"] = {}
        config["channels"][channel_type] = {
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }
        save_config(config)
        console.print(f"[green]✓ 通道 '{channel_type}' 已启用[/green]")
        console.print("[dim]iMessage 无需配置凭证[/dim]")

    elif channel_type == "wecom":
        corp_id = click.prompt("Corp ID", type=str)
        agent_id = click.prompt("Agent ID", type=int)
        secret = click.prompt("Secret", type=str, hide_input=True)

        with console.status("[bold green]正在验证凭证..."):
            try:
                response = httpx.get(
                    "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                    params={"corpid": corp_id, "corpsecret": secret},
                    timeout=10.0,
                )
                data = response.json()
                if data.get("errcode", 0) != 0:
                    raise click.ClickException(
                        f"验证失败: {data.get('errmsg', '未知错误')} (errcode={data.get('errcode')})"
                    )
                console.print("[green]✓ 凭证验证成功[/green]")
            except httpx.RequestError as e:
                raise click.ClickException(f"连接失败: {e}") from e

        if "channels" not in config:
            config["channels"] = {}
        config["channels"]["wecom"] = {
            "corp_id": corp_id,
            "agent_id": agent_id,
            "secret": secret,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }
        save_config(config)
        console.print("[green]✓ 通道 'wecom' 配置完成[/green]")

        if prompt_confirm("是否立即获取用户 ID (capture)?"):
            _do_wecom_capture(alias="me")


def _do_wecom_capture(alias: str) -> None:
    from claw_cron.channels import get_channel
    from claw_cron.channels.exceptions import ChannelError
    _cfg = load_config().get("channels", {}).get("wecom", {})
    ch = get_channel("wecom", config=_cfg if _cfg else None)
    try:
        userid = asyncio.run(ch.capture_openid())
        console.print(f"[green]✓ UserID 已捕获: [bold]{userid}[/bold][/green]")
        save_contact(Contact(
            openid=userid,
            channel="wecom",
            alias=alias,
            created=datetime.now().isoformat(),
        ))
        console.print(f"[green]✓ 联系人已保存为 '{alias}'[/green]")
    except ChannelError as e:
        console.print(f"[red]Capture 失败: {e}[/red]")


@channels.command("list")
def list_channels() -> None:
    """List all registered channels with configuration status."""
    config = load_config()
    channels_config = config.get("channels", {})
    contacts_data = load_contacts()

    # Create table with enhanced columns
    table = Table(title="消息通道")
    table.add_column("Channel", style="cyan", width=10)
    table.add_column("Status", width=14)
    table.add_column("Config", width=16)
    table.add_column("Contacts", justify="right", width=8)
    table.add_column("Created", width=10)

    # List all registered channels (not just configured ones)
    for channel_id in sorted(CHANNEL_REGISTRY.keys()):
        # Get configuration status
        icon, status_text = get_channel_status(channel_id)

        # Build status display with color
        if icon == "✓":
            status_display = f"[green]{icon} {status_text}[/green]"
        elif icon == "⚠":
            status_display = f"[yellow]{icon} {status_text}[/yellow]"
        elif icon == "✗":
            status_display = f"[red]{icon} {status_text}[/red]"
        else:  # ○
            status_display = f"[dim]{icon} {status_text}[/dim]"

        # Get config display value
        channel_cfg = channels_config.get(channel_id, {})
        if channel_id == "qqbot":
            app_id = channel_cfg.get("app_id", "")
            config_display = f"{app_id[:8]}..." if len(str(app_id)) > 8 else str(app_id) or "-"
        elif channel_id == "feishu":
            app_id = channel_cfg.get("app_id", "")
            config_display = f"{app_id[:8]}..." if len(str(app_id)) > 8 else str(app_id) or "-"
        elif channel_id == "imessage":
            config_display = "[dim]无需凭证[/dim]"
        else:
            config_display = "-"

        # Count contacts
        contact_count = sum(1 for c in contacts_data.values() if c.channel == channel_id)

        # Get created date
        created_at = channel_cfg.get("created_at", "")
        created_display = created_at[:10] if created_at else "-"  # Just date part

        table.add_row(
            channel_id,
            status_display,
            config_display,
            str(contact_count),
            created_display,
        )

    console.print(table)


@channels.command()
@click.argument("channel_type", type=click.Choice(["qqbot", "feishu", "imessage", "email", "wecom"]))
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
        if not prompt_confirm(f"Delete channel '{channel_type}'?"):
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
@click.argument("channel_type", type=click.Choice(["qqbot", "feishu", "imessage", "email", "wecom"]))
def verify(channel_type: str) -> None:
    """Verify channel credentials and connectivity.

    CHANNEL_TYPE is the channel to verify (e.g., 'qqbot', 'feishu', 'imessage').

    For QQ Bot: Validates app_id and client_secret with QQ API.
    For Feishu: Validates app_id and app_secret with Feishu API.
    For iMessage: Checks if running on macOS with Messages app available.
    """
    config = load_config()
    channels_config = config.get("channels", {})

    if channel_type not in channels_config:
        console.print(f"[yellow]通道 '{channel_type}' 未配置[/yellow]")
        console.print("[dim]运行 'claw-cron channels add' 进行配置[/dim]")
        raise SystemExit(1)

    console.print(f"[bold]验证通道 '{channel_type}'...[/bold]\n")

    if channel_type == "qqbot":
        qq_config = channels_config["qqbot"]
        app_id = qq_config.get("app_id")
        client_secret = qq_config.get("client_secret")

        if not app_id or not client_secret:
            console.print("[red]✗ 配置不完整：缺少 app_id 或 client_secret[/red]")
            raise SystemExit(1)

        with console.status("[bold green]正在验证凭证..."):
            try:
                response = httpx.post(
                    "https://bots.qq.com/app/getAppAccessToken",
                    json={"appId": app_id, "clientSecret": client_secret},
                    timeout=10.0,
                )
                data = response.json()

                if data.get("code", 0) != 0:
                    console.print(f"[red]✗ 验证失败: {data.get('message', '未知错误')}[/red]")
                    console.print(f"[dim]错误码: {data.get('code')}[/dim]")
                    raise SystemExit(1)

                console.print("[green]✓ 凭证验证成功[/green]")
                console.print(f"[dim]AppID: {app_id}[/dim]")

                # Optionally show token info
                access_token = data.get("access_token", "")
                if access_token:
                    console.print(f"[dim]Access Token: {access_token[:20]}...[/dim]")

            except httpx.RequestError as e:
                console.print(f"[red]✗ 连接失败: {e}[/red]")
                raise SystemExit(1)

    elif channel_type == "feishu":
        feishu_config = channels_config["feishu"]
        app_id = feishu_config.get("app_id")
        app_secret = feishu_config.get("app_secret")

        if not app_id or not app_secret:
            console.print("[red]✗ 配置不完整：缺少 app_id 或 app_secret[/red]")
            raise SystemExit(1)

        with console.status("[bold green]正在验证凭证..."):
            try:
                response = httpx.post(
                    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                    json={"app_id": app_id, "app_secret": app_secret},
                    timeout=10.0,
                )
                data = response.json()

                if data.get("code", 0) != 0:
                    console.print(f"[red]✗ 验证失败: {data.get('message', '未知错误')}[/red]")
                    console.print(f"[dim]错误码: {data.get('code')}[/dim]")
                    raise SystemExit(1)

                console.print("[green]✓ 凭证验证成功[/green]")
                console.print(f"[dim]App ID: {app_id}[/dim]")

                access_token = data.get("tenant_access_token", "")
                if access_token:
                    console.print(f"[dim]Tenant Access Token: {access_token[:20]}...[/dim]")

            except httpx.RequestError as e:
                console.print(f"[red]✗ 连接失败: {e}[/red]")
                raise SystemExit(1)

    elif channel_type == "imessage":
        # iMessage doesn't require credentials, just check platform
        import platform

        if platform.system() != "Darwin":
            console.print("[red]✗ iMessage 仅在 macOS 上可用[/red]")
            raise SystemExit(1)

        console.print("[green]✓ iMessage 可用[/green]")
        console.print("[dim]平台: macOS[/dim]")

    elif channel_type == "email":
        email_cfg = channels_config["email"]
        required_fields = ["host", "username", "password", "from_email"]
        missing = [f for f in required_fields if not email_cfg.get(f)]
        if missing:
            console.print(f"[red]✗ 配置不完整：缺少 {', '.join(missing)}[/red]")
            raise SystemExit(1)

        with console.status("[bold green]正在发送验证邮件..."):
            try:
                import asyncio as _asyncio
                from claw_cron.channels.email import EmailChannel, EmailConfig
                test_config = EmailConfig(**{k: v for k, v in email_cfg.items() if k not in ("created_at", "enabled")})
                channel = EmailChannel(test_config)
                result = _asyncio.run(channel.send_text(
                    email_cfg["from_email"],
                    "claw-cron 邮件通道验证邮件",
                ))
                if not result.success:
                    console.print(f"[red]✗ 验证失败: {result.error}[/red]")
                    raise SystemExit(1)
                console.print("[green]✓ 验证邮件已发送[/green]")
                console.print(f"[dim]SMTP Host: {email_cfg['host']}:{email_cfg.get('port', 587)}[/dim]")
                console.print(f"[dim]From: {email_cfg['from_email']}[/dim]")
            except SystemExit:
                raise
            except Exception as e:
                console.print(f"[red]✗ 连接失败: {e}[/red]")
                raise SystemExit(1)

    elif channel_type == "wecom":
        wecom_cfg = channels_config["wecom"]
        corp_id = wecom_cfg.get("corp_id")
        secret = wecom_cfg.get("secret")
        if not corp_id or not secret:
            console.print("[red]✗ 配置不完整：缺少 corp_id 或 secret[/red]")
            raise SystemExit(1)
        with console.status("[bold green]正在验证凭证..."):
            try:
                response = httpx.get(
                    "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                    params={"corpid": corp_id, "corpsecret": secret},
                    timeout=10.0,
                )
                data = response.json()
                if data.get("errcode", 0) != 0:
                    console.print(f"[red]✗ 验证失败: {data.get('errmsg')} (errcode={data.get('errcode')})[/red]")
                    raise SystemExit(1)
                console.print("[green]✓ 凭证验证成功[/green]")
                console.print(f"[dim]Corp ID: {corp_id}[/dim]")
            except httpx.RequestError as e:
                console.print(f"[red]✗ 连接失败: {e}[/red]")
                raise SystemExit(1)

    console.print(f"\n[green]✓ 通道 '{channel_type}' 验证通过[/green]")


@channels.command()
@click.option(
    "--alias",
    prompt="Save as contact alias",
    default="me",
    help="Alias name for the captured contact",
)
def capture(alias: str) -> None:
    """Connect to channel and capture user openid.

    This command starts a WebSocket connection and waits for you
    to send a message to the bot. When received, your openid is
    captured and saved as a contact alias.

    Example:
        claw-cron channels capture --alias my_friend
        # Then send any message to your QQ Bot
    """
    from claw_cron.channels import get_channel
    from claw_cron.channels.exceptions import ChannelConfigError, ChannelError

    channel_type = prompt_capture_channel_select()
    config = load_config()
    channel_cfg = config.get("channels", {}).get(channel_type, {})
    channel = get_channel(channel_type, config=channel_cfg if channel_cfg else None)
    display_name = CHANNEL_DISPLAY_NAMES.get(channel_type, channel_type)

    if not channel.supports_capture:
        reasons = {
            "imessage": "iMessage 使用手机号直接发送，无需获取用户 ID",
            "email": "邮件使用邮箱地址直接发送",
        }
        reason = reasons.get(channel_type, "此通道不需要 capture")
        console.print(f"[yellow]此通道不需要 capture。{reason}[/yellow]")
        return

    console.print(f"\n[dim]请向你的 {display_name} 机器人发送任意消息[/dim]")
    console.print("[dim]按 Ctrl+C 取消[/dim]\n")

    try:
        with console.status(f"[bold green]等待来自 {display_name} 的消息..."):
            openid = asyncio.run(channel.capture_openid())
        console.print(f"[green]✓ OpenID 已捕获: [bold]{openid}[/bold][/green]")

        contact = Contact(
            openid=openid,
            channel=channel_type,
            alias=alias,
            created=datetime.now().isoformat(),
        )
        save_contact(contact)
        console.print(f"[green]✓ 联系人已保存为 '[bold]{alias}[/bold]'[/green]")
        console.print(f"[dim]现在可以使用 'claw-cron remind --recipient {alias}'[/dim]")
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
    except ChannelError as e:
        if "timed out" in str(e).lower():
            console.print(f"\n[red]✗ Capture 超时（5 分钟），请确认机器人在线后重试[/red]")
        else:
            console.print(f"[red]Capture 失败: {e}[/red]")
        raise SystemExit(1)
    except ChannelConfigError as e:
        console.print(f"[red]Capture 失败: {e}[/red]")
        raise SystemExit(1)



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

    if not force and not prompt_confirm(f"Delete contact '{alias}'?"):
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
