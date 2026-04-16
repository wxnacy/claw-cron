# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""remind command — create a scheduled reminder task."""

from __future__ import annotations

import click
from rich.console import Console

from claw_cron.contacts import resolve_recipient
from claw_cron.notifier import NotifyConfig
from claw_cron.storage import Task, add_task

console = Console()


@click.command()
@click.option("--name", required=True, help="Unique reminder name")
@click.option("--cron", required=True, help="Cron expression (e.g., '0 8 * * *')")
@click.option(
    "--message", required=True, help="Reminder message (supports {{ date }}, {{ time }})"
)
@click.option(
    "--channel", required=True, help="Notification channel (imessage, qqbot)"
)
@click.option(
    "--recipient",
    "recipients",
    required=True,
    multiple=True,
    help="Notification recipient (openid, 'c2c:OPENID', 'group:OPENID', or contact alias)",
)
def remind(
    name: str,
    cron: str,
    message: str,
    channel: str,
    recipients: tuple[str, ...],
) -> None:
    """Create a scheduled reminder task.

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
    """
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
