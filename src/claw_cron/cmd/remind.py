# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""remind command — create a scheduled reminder task."""

from __future__ import annotations

import click
from rich.console import Console

from claw_cron.config import load_config
from claw_cron.contacts import load_contacts, resolve_recipient
from claw_cron.notifier import NotifyConfig
from claw_cron.prompt import prompt_confirm, prompt_cron, prompt_select, prompt_text
from claw_cron.storage import Task, add_task

console = Console()


def _remind_interactive() -> None:
    """Interactive guided creation of a reminder task."""
    console.print("[bold cyan]创建定时提醒[/bold cyan]\n")

    # 1. Input task name
    name = prompt_text("提醒名称 (唯一标识)")

    # 2. Select cron expression
    console.print("\n[bold]选择执行时间:[/bold]")
    cron = prompt_cron()

    # 3. Input reminder message
    message = prompt_text(
        "提醒内容 (支持 {{ date }}, {{ time }} 变量)"
    )

    # 4. Select notification channel
    config = load_config()
    channels_config = config.get("channels", {})
    if not channels_config:
        console.print("[red]未配置通知通道。请先运行 'claw-cron channels add'[/red]")
        raise SystemExit(1)

    available_channels = list(channels_config.keys())
    if len(available_channels) == 1:
        channel = available_channels[0]
        console.print(f"[dim]使用通道: {channel}[/dim]")
    else:
        console.print("\n[bold]选择通知通道:[/bold]")
        channel = prompt_select("通道", choices=available_channels)

    # 5. Select recipient
    contacts_data = load_contacts()
    channel_contacts = {
        alias: c for alias, c in contacts_data.items()
        if c.channel == channel
    }

    if channel_contacts:
        console.print("\n[bold]选择收件人:[/bold]")
        recipient_choices = list(channel_contacts.keys()) + ["[手动输入]"]
        selected = prompt_select("收件人", choices=recipient_choices)

        if selected == "[手动输入]":
            recipient_input = prompt_text(
                "输入收件人 (OpenID 格式如 'c2c:ABC123' 或 'group:XYZ789')"
            )
            recipients = [recipient_input]
        else:
            recipients = [selected]
    else:
        console.print("[dim]未找到已保存联系人[/dim]")
        recipient_input = prompt_text(
            "输入收件人 (OpenID 格式如 'c2c:ABC123' 或 'group:XYZ789')"
        )
        recipients = [recipient_input]

    # 6. Preview and confirm
    console.print(f"\n[bold]确认创建提醒:[/bold]")
    console.print(f"  名称: {name}")
    console.print(f"  时间: {cron}")
    console.print(f"  内容: {message}")
    console.print(f"  通道: {channel}")
    console.print(f"  收件人: {', '.join(recipients)}")

    if not prompt_confirm("\n确认创建?", default=True):
        console.print("[dim]已取消[/dim]")
        return

    # 7. Create task
    resolved_recipients: list[str] = []
    for recipient in recipients:
        try:
            resolved = resolve_recipient(recipient, channel)
            resolved_recipients.append(resolved)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise SystemExit(1)

    notify = NotifyConfig(channel=channel, recipients=resolved_recipients)
    task = Task(
        name=name,
        cron=cron,
        type="reminder",
        message=message,
        notify=notify,
    )
    add_task(task)
    console.print(f"\n[green]提醒 '{name}' 创建成功[/green]")





@click.command()
@click.option("--name", default=None, help="Unique reminder name")
@click.option("--cron", default=None, help="Cron expression (e.g., '0 8 * * *')")
@click.option(
    "--message", default=None, help="Reminder message (supports {{ date }}, {{ time }})"
)
@click.option(
    "--channel", default=None, help="Notification channel (imessage, qqbot)"
)
@click.option(
    "--recipient",
    "recipients",
    default=None,
    multiple=True,
    help="Notification recipient (openid, 'c2c:OPENID', 'group:OPENID', or contact alias)",
)
def remind(
    name: str | None,
    cron: str | None,
    message: str | None,
    channel: str | None,
    recipients: tuple[str, ...] | None,
) -> None:
    """Create a scheduled reminder task.

    Direct mode: provide --name, --cron, --message, --channel, --recipient to create directly.
    Interactive mode: omit any required option to start guided creation.

    Reminders are tasks that send a notification message at the scheduled time,
    without running any script or AI command.

    The message supports template variables:
      - {{ date }} : Current date (YYYY-MM-DD)
      - {{ time }} : Current time (HH:MM:SS)

    Recipients can be:
      - OpenID format: "c2c:ABC123" or "group:XYZ789"
      - Contact alias: "me", "john", etc. (saved via 'claw-cron channels capture')

    Examples:
        # Daily morning reminder via iMessage
        claw-cron remind --name morning --cron "0 8 * * *" \\
            --message "Good morning! Today is {{ date }}" \\
            --channel imessage --recipient "+8613812345678"

        # Weekly meeting reminder via QQ Bot
        claw-cron remind --name weekly-meeting --cron "0 14 * * 1" \\
            --message "Weekly meeting starting at {{ time }}" \\
            --channel qqbot --recipient "group:123456"

        # Using contact alias
        claw-cron remind --name test --cron "0 8 * * *" \\
            --message "Hello" --channel qqbot --recipient me

        # Interactive mode
        claw-cron remind
    """
    # Check if entering interactive mode
    if not all([name, cron, message, channel, recipients]):
        return _remind_interactive()

    # Direct mode: proceed with provided arguments
    # Resolve aliases to openid format
    resolved_recipients: list[str] = []
    for recipient in recipients:
        try:
            resolved = resolve_recipient(recipient, channel)
            resolved_recipients.append(resolved)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise SystemExit(1)

    notify = NotifyConfig(channel=channel, recipients=resolved_recipients)

    task = Task(
        name=name,
        cron=cron,
        type="reminder",
        message=message,
        notify=notify,
    )

    add_task(task)
    console.print(f"[green]Reminder '{name}' created.[/green]")
    console.print(f"[dim]  Cron: {cron}[/dim]")
    console.print(f"[dim]  Channel: {channel}[/dim]")
    console.print(f"[dim]  Recipients: {', '.join(recipients)}[/dim]")
    # Show resolved format if alias was used
    if resolved_recipients != list(recipients):
        console.print(f"[dim]  Resolved: {', '.join(resolved_recipients)}[/dim]")
