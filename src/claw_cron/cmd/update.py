# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""update command — modify fields of an existing scheduled task."""

from __future__ import annotations

import click
from rich.console import Console

from claw_cron.storage import (
    get_notify_list,
    get_task,
    notify_add,
    notify_clear,
    notify_remove,
    notify_update,
    update_task,
)

console = Console()


@click.command()
@click.argument("name")
@click.option("--cron", default=None, help="New cron expression (e.g. '0 8 * * *')")
@click.option("--enabled", default=None, type=bool, help="Enable or disable the task (true/false)")
@click.option("--message", default=None, help="New notification message template")
@click.option("--script", default=None, help="New shell script content (command type)")
@click.option("--prompt", default=None, help="New AI prompt content (chat type)")
# notify options
@click.option("--notify-add", "notify_add_channel", default=None, metavar="CHANNEL", help="Add a notify channel")
@click.option("--notify-remove", "notify_remove_channel", default=None, metavar="CHANNEL", help="Remove a notify channel")
@click.option("--notify-channel", default=None, metavar="CHANNEL", help="Target channel for --notify-recipient / --notify-when")
@click.option("--notify-recipient", default=None, metavar="RECIPIENT", help="Recipient for --notify-add or --notify-channel update")
@click.option("--notify-when", default=None, metavar="EXPR", help="Condition expression (empty string to clear)")
@click.option("--notify-clear", "do_notify_clear", is_flag=True, help="Remove all notify configs")
def update(
    name: str,
    cron: str | None,
    enabled: bool | None,
    message: str | None,
    script: str | None,
    prompt: str | None,
    notify_add_channel: str | None,
    notify_remove_channel: str | None,
    notify_channel: str | None,
    notify_recipient: str | None,
    notify_when: str | None,
    do_notify_clear: bool,
) -> None:
    """Update fields of an existing task by NAME.

    Omit all options to enter interactive mode.

    \b
    Notify examples:
      --notify-add qqbot --notify-recipient c2c:XXX
      --notify-add system
      --notify-remove qqbot
      --notify-channel qqbot --notify-recipient c2c:NEW
      --notify-channel qqbot --notify-when "signed_in == false"
      --notify-channel qqbot --notify-when ""   (clear condition)
      --notify-clear
    """
    task = get_task(name)
    if task is None:
        console.print(f"[red]Task '{name}' not found.[/red]")
        raise SystemExit(1)

    has_any_option = any([
        cron, enabled is not None, message, script, prompt,
        notify_add_channel, notify_remove_channel, notify_channel,
        notify_when is not None, do_notify_clear,
    ])

    if not has_any_option:
        return _update_interactive(name, task)

    # --- scalar field updates ---
    scalar_updates: dict = {}
    if cron is not None:
        scalar_updates["cron"] = cron
    if enabled is not None:
        scalar_updates["enabled"] = enabled
    if message is not None:
        scalar_updates["message"] = message
    if script is not None:
        scalar_updates["script"] = script
    if prompt is not None:
        scalar_updates["prompt"] = prompt

    if scalar_updates:
        update_task(name, **scalar_updates)
        for key, value in scalar_updates.items():
            console.print(f"  [dim]{key}[/dim] = {value}")

    # --- notify operations ---
    if do_notify_clear:
        notify_clear(name)
        console.print("  [dim]notify[/dim] = cleared")

    elif notify_add_channel:
        if notify_add_channel == "system":
            recipients = [notify_recipient or "local"]
        elif notify_recipient:
            recipients = [notify_recipient]
        else:
            console.print("[red]--notify-add requires --notify-recipient (except for system channel)[/red]")
            raise SystemExit(1)
        when = notify_when if notify_when else None
        ok = notify_add(name, notify_add_channel, recipients, when)
        if not ok:
            console.print(f"[yellow]Channel '{notify_add_channel}' already exists. Use --notify-channel to modify.[/yellow]")
            raise SystemExit(1)
        console.print(f"  [dim]notify[/dim] + {notify_add_channel} -> {recipients}")

    elif notify_remove_channel:
        ok = notify_remove(name, notify_remove_channel)
        if not ok:
            console.print(f"[yellow]Channel '{notify_remove_channel}' not found in notify config.[/yellow]")
            raise SystemExit(1)
        console.print(f"  [dim]notify[/dim] - {notify_remove_channel}")

    elif notify_channel:
        if notify_recipient is None and notify_when is None:
            console.print("[red]--notify-channel requires --notify-recipient or --notify-when[/red]")
            raise SystemExit(1)
        recipients = [notify_recipient] if notify_recipient else None
        clear_when = notify_when == ""
        when = notify_when if notify_when and not clear_when else None
        ok = notify_update(name, notify_channel, recipients=recipients, when=when, clear_when=clear_when)
        if not ok:
            console.print(f"[yellow]Channel '{notify_channel}' not found in notify config.[/yellow]")
            raise SystemExit(1)
        console.print(f"  [dim]notify[/dim] ~ {notify_channel} updated")

    console.print(f"[green]Task '{name}' updated.[/green]")


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def _update_interactive(name: str, task) -> None:  # type: ignore[no-untyped-def]
    from InquirerPy import inquirer

    from claw_cron.prompt import prompt_cron, prompt_text

    # Build field choices with current values
    def _short(v: object, maxlen: int = 40) -> str:
        s = str(v) if v is not None else "null"
        return s if len(s) <= maxlen else s[:maxlen - 1] + "…"

    notify_summary = _notify_summary(task)

    # Use plain strings for checkbox — Choice objects cause keybinding issues in some terminals
    field_map = {
        f"cron     [{_short(task.cron)}]":    "cron",
        f"enabled  [{task.enabled}]":          "enabled",
        f"message  [{_short(task.message)}]":  "message",
        f"script   [{_short(task.script)}]":   "script",
        f"prompt   [{_short(task.prompt)}]":   "prompt",
        f"notify   [{notify_summary}]":        "notify",
    }

    while True:
        selected_labels: list[str] = inquirer.checkbox(
            message="选择要修改的字段:",
            choices=list(field_map.keys()),
            instruction="(空格选中/取消，↑↓移动，回车确认)",
        ).execute()
        if selected_labels:
            break
        console.print("[yellow]请至少选择一个字段[/yellow]")

    selected_fields = [field_map[label] for label in selected_labels]

    scalar_updates: dict = {}

    for field in selected_fields:
        if field == "cron":
            scalar_updates["cron"] = prompt_cron()

        elif field == "enabled":
            scalar_updates["enabled"] = inquirer.confirm(
                message="启用任务?", default=task.enabled
            ).execute()

        elif field == "message":
            scalar_updates["message"] = prompt_text("新 message:", default=task.message or "")

        elif field == "script":
            scalar_updates["script"] = prompt_text("新 script:", default=task.script or "")

        elif field == "prompt":
            scalar_updates["prompt"] = prompt_text("新 prompt:", default=task.prompt or "")

        elif field == "notify":
            _notify_interactive(name, task)

    if scalar_updates:
        update_task(name, **scalar_updates)
        for key, value in scalar_updates.items():
            console.print(f"  [dim]{key}[/dim] = {value}")

    console.print(f"[green]Task '{name}' updated.[/green]")


def _notify_summary(task) -> str:  # type: ignore[no-untyped-def]
    configs = get_notify_list(task)
    if not configs:
        return "none"
    return ", ".join(c.channel for c in configs)


def _notify_interactive(name: str, task) -> None:  # type: ignore[no-untyped-def]
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice

    from claw_cron.contacts import load_contacts
    from claw_cron.prompt import prompt_channel_select, prompt_text

    while True:
        configs = get_notify_list(get_task(name))  # type: ignore[arg-type]
        summary = ", ".join(c.channel for c in configs) if configs else "none"
        console.print(f"\n[bold]通知配置[/bold] (当前: {summary})")

        action = inquirer.select(
            message="操作:",
            choices=[
                Choice(value="add",    name="添加渠道"),
                Choice(value="remove", name="删除渠道"),
                Choice(value="edit",   name="修改渠道"),
                Choice(value="clear",  name="清空所有"),
                Choice(value="done",   name="完成"),
            ],
        ).execute()

        if action == "done":
            break

        elif action == "clear":
            notify_clear(name)
            console.print("  [dim]已清空所有通知配置[/dim]")

        elif action == "add":
            channel = prompt_channel_select()
            if any(c.channel == channel for c in configs):
                console.print(f"[yellow]'{channel}' 已存在，请用「修改渠道」[/yellow]")
                continue
            recipients = _prompt_recipients(channel)
            when = _prompt_when()
            notify_add(name, channel, recipients, when or None)
            console.print(f"  [dim]已添加 {channel}[/dim]")

        elif action == "remove":
            if not configs:
                console.print("[yellow]没有可删除的通知配置[/yellow]")
                continue
            channel = inquirer.select(
                message="选择要删除的渠道:",
                choices=[c.channel for c in configs],
            ).execute()
            notify_remove(name, channel)
            console.print(f"  [dim]已删除 {channel}[/dim]")

        elif action == "edit":
            if not configs:
                console.print("[yellow]没有可修改的通知配置[/yellow]")
                continue
            channel = inquirer.select(
                message="选择要修改的渠道:",
                choices=[c.channel for c in configs],
            ).execute()
            cfg = next(c for c in configs if c.channel == channel)

            edit_map = {
                f"recipient  [{', '.join(cfg.recipients)}]": "recipient",
                f"when       [{cfg.when or 'null'}]":        "when",
            }
            what_labels = inquirer.checkbox(
                message=f"修改 {channel} 的哪些项:",
                choices=list(edit_map.keys()),
                instruction="(空格选中/取消，回车确认)",
            ).execute()
            if not what_labels:
                console.print("[yellow]未选择任何项，跳过[/yellow]")
                continue
            what = [edit_map[l] for l in what_labels]

            new_recipients = None
            new_when = None
            clear_when = False

            if "recipient" in what:
                new_recipients = _prompt_recipients(channel, current=cfg.recipients)

            if "when" in what:
                raw = prompt_text("条件表达式 (留空清除):", default=cfg.when or "")
                clear_when = raw == ""
                new_when = raw if raw else None

            notify_update(name, channel, recipients=new_recipients, when=new_when, clear_when=clear_when)
            console.print(f"  [dim]{channel} 已更新[/dim]")


def _prompt_recipients(channel: str, current: list[str] | None = None) -> list[str]:
    """Prompt for recipient(s) for a given channel."""
    from claw_cron.contacts import load_contacts
    from claw_cron.prompt import prompt_text

    if channel == "system":
        return ["local"]

    contacts_data = load_contacts()
    channel_contacts = {
        alias: c for alias, c in contacts_data.items() if c.channel == channel
    }

    if channel_contacts:
        from InquirerPy import inquirer
        choices = list(channel_contacts.keys()) + ["[手动输入]"]
        default = choices[0] if not current else (current[0] if current[0] in choices else choices[0])
        selected = inquirer.select(
            message="选择收件人:", choices=choices, default=default
        ).execute()
        if selected != "[手动输入]":
            return [selected]

    raw = prompt_text(
        "输入收件人 (如 c2c:ABC123):",
        default=current[0] if current else None,
    )
    return [raw]


def _prompt_when() -> str:
    """Prompt for optional when condition."""
    from claw_cron.prompt import prompt_confirm, prompt_text

    if not prompt_confirm("设置触发条件 (when)?", default=False):
        return ""
    return prompt_text("条件表达式 (如 signed_in == false):")
