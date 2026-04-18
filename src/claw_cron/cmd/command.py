# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""command command — create a command-type scheduled task."""

from __future__ import annotations

import click
from rich.console import Console

from claw_cron.config import load_config
from claw_cron.contacts import load_contacts, resolve_recipient
from claw_cron.notifier import NotifyConfig
from claw_cron.prompt import prompt_text, prompt_confirm, prompt_select, prompt_cron
from claw_cron.storage import Task, add_task

console = Console()


@click.command()
@click.option("--name", default=None, help="Unique task name")
@click.option("--cron", default=None, help="Cron expression (e.g., '0 8 * * *')")
@click.option("--script", default=None, help="Shell command to execute")
@click.option("--channel", default="system", help="Notification channel (default: system)")
@click.option(
    "--recipient",
    "recipients",
    multiple=True,
    default=("local",),
    help="Notification recipient (default: local for system channel)",
)
@click.option("--no-notify", is_flag=True, help="Disable notification")
def command(
    name: str | None,
    cron: str | None,
    script: str | None,
    channel: str,
    recipients: tuple[str, ...],
    no_notify: bool,
) -> None:
    """Create a command-type scheduled task.

    Direct mode: provide --name, --cron, --script to create directly.
    Interactive mode: omit required options for guided creation.

    By default, uses 'system' channel for desktop notifications.
    Use --no-notify to disable notifications.

    Examples:
        # Direct mode with default system notification
        claw-cron command --name backup --cron "0 2 * * *" --script "backup.sh"

        # Disable notification
        claw-cron command --name backup --cron "0 2 * * *" \\
            --script "backup.sh" --no-notify

        # With QQ Bot notification
        claw-cron command --name health-check --cron "*/30 * * * *" \\
            --script "curl -s https://api.example.com/health" \\
            --channel qqbot --recipient me

        # Interactive mode
        claw-cron command
    """
    # Check if entering interactive mode
    if not all([name, cron, script]):
        return _command_interactive(name, cron, script, channel if not no_notify else None, recipients if not no_notify else None)

    # Direct mode
    _command_direct(name, cron, script, None if no_notify else channel, recipients if not no_notify else None)


def _command_direct(
    name: str,
    cron: str,
    script: str,
    channel: str | None,
    recipients: tuple[str, ...] | None,
) -> None:
    """Create command task directly from arguments."""
    notify = None
    if channel and recipients:
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
        type="command",
        script=script,
        notify=notify,
    )
    add_task(task)
    console.print(f"[green]Command task '{name}' created.[/green]")
    console.print(f"[dim]  Cron: {cron}[/dim]")
    console.print(f"[dim]  Script: {script}[/dim]")
    if notify:
        console.print(f"[dim]  Notify: {channel} -> {', '.join(recipients or [])}[/dim]")
    else:
        console.print(f"[dim]  Notify: disabled[/dim]")


def _command_interactive(
    name: str | None = None,
    cron: str | None = None,
    script: str | None = None,
    channel: str | None = None,
    recipients: tuple[str, ...] | None = None,
) -> None:
    """Interactive guided creation for command task."""
    console.print("[bold cyan]创建命令任务[/bold cyan]\n")

    # 1. Task name
    if not name:
        name = prompt_text("任务名称 (唯一标识)")
    else:
        console.print(f"[dim]名称: {name}[/dim]")

    # 2. Cron expression
    if not cron:
        console.print("\n[bold]选择执行时间:[/bold]")
        cron = prompt_cron()
    else:
        console.print(f"[dim]时间: {cron}[/dim]")

    # 3. Script
    if not script:
        script = prompt_text("Shell 命令")

    # 4. Optional notification
    notify = None
    if prompt_confirm("\n配置执行通知?", default=True):
        config = load_config()
        channels_config = config.get("channels", {})

        # Include system channel as default option
        available_channels = list(channels_config.keys())
        if "system" not in available_channels:
            available_channels.insert(0, "system")

        if len(available_channels) == 1:
            selected_channel = available_channels[0]
        else:
            console.print("\n[bold]选择通知通道:[/bold]")
            selected_channel = prompt_select("通道", choices=available_channels, default="system")

            # Select recipient
            contacts_data = load_contacts()
            channel_contacts = {
                alias: c for alias, c in contacts_data.items()
                if c.channel == selected_channel
            }

            # System channel doesn't need recipient selection
            if selected_channel == "system":
                selected_recipients = ["local"]
            elif channel_contacts:
                console.print("\n[bold]选择收件人:[/bold]")
                recipient_choices = list(channel_contacts.keys()) + ["[手动输入]"]
                selected = prompt_select("收件人", choices=recipient_choices)

                if selected == "[手动输入]":
                    recipient_input = prompt_text(
                        "输入收件人 (OpenID 格式如 'c2c:ABC123')"
                    )
                    selected_recipients = [recipient_input]
                else:
                    selected_recipients = [selected]
            else:
                recipient_input = prompt_text(
                    "输入收件人 (OpenID 格式如 'c2c:ABC123')"
                )
                selected_recipients = [recipient_input]

            # Resolve recipients
            resolved: list[str] = []
            for r in selected_recipients:
                try:
                    resolved.append(resolve_recipient(r, selected_channel))
                except ValueError as e:
                    console.print(f"[red]Error: {e}[/red]")
                    raise SystemExit(1)

            notify = NotifyConfig(channel=selected_channel, recipients=resolved)

    # 5. Preview and confirm
    console.print(f"\n[bold]确认创建任务:[/bold]")
    console.print(f"  名称: {name}")
    console.print(f"  时间: {cron}")
    console.print(f"  命令: {script}")
    if notify:
        console.print(f"  通知: {notify.channel}")

    if not prompt_confirm("\n确认创建?", default=True):
        console.print("[dim]已取消[/dim]")
        return

    # 6. Create task
    task = Task(
        name=name,
        cron=cron,
        type="command",
        script=script,
        notify=notify,
    )
    add_task(task)
    console.print(f"\n[green]任务 '{name}' 创建成功[/green]")
