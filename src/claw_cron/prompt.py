# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Interactive prompt utilities using InquirerPy.

This module provides wrapper functions for common interactive prompts,
including a specialized cron expression selector with human-readable presets.
"""

from __future__ import annotations

from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from claw_cron.channels import CHANNEL_REGISTRY, get_channel_status


def prompt_text(message: str, default: str | None = None) -> str:
    """Prompt user for text input.

    Args:
        message: The prompt message to display.
        default: Optional default value.

    Returns:
        The user's input string.
    """
    if default is not None:
        return inquirer.text(message=message, default=default).execute()
    return inquirer.text(message=message).execute()


def prompt_confirm(message: str, default: bool = True) -> bool:
    """Prompt user for confirmation.

    Args:
        message: The prompt message to display.
        default: Default value (True for yes, False for no).

    Returns:
        Boolean indicating user's choice.
    """
    return inquirer.confirm(message=message, default=default).execute()


def prompt_select(message: str, choices: list[str], default: str | None = None) -> str:
    """Prompt user to select a single option.

    Args:
        message: The prompt message to display.
        choices: List of available choices.
        default: Optional default choice to pre-select.

    Returns:
        The selected choice string.
    """
    if default is not None:
        return inquirer.select(message=message, choices=choices, default=default).execute()
    return inquirer.select(message=message, choices=choices).execute()


def prompt_multiselect(message: str, choices: list[str]) -> list[str]:
    """Prompt user to select multiple options.

    Args:
        message: The prompt message to display.
        choices: List of available choices.

    Returns:
        List of selected choice strings.
    """
    return inquirer.checkbox(message=message, choices=choices).execute()


def prompt_fuzzy_select(message: str, choices: list[str]) -> str | None:
    """Prompt user to select a single option with fuzzy filtering.

    Supports arrow-key navigation and typing to filter the list.

    Args:
        message: The prompt message to display.
        choices: List of available choices.

    Returns:
        The selected choice string, or None if the user cancels.
    """
    try:
        return inquirer.fuzzy(message=message, choices=choices).execute()
    except KeyboardInterrupt:
        return None


def prompt_cron() -> str:
    """Prompt user to select a cron expression.

    Provides a list of common cron presets with human-readable descriptions,
    plus an option to enter a custom expression.

    Presets:
        - 每分钟: * * * * *
        - 每小时整点: 0 * * * *
        - 每天早上8点: 0 8 * * *
        - 每天中午12点: 0 12 * * *
        - 每天晚上6点: 0 18 * * *
        - 每周一早上9点: 0 9 * * 1
        - 工作日早上9点: 0 9 * * 1-5
        - 每月1号: 0 0 1 * *
        - 自定义: Enter custom expression

    Returns:
        The selected or entered cron expression string.
    """
    choices = [
        Choice(value="* * * * *", name="每分钟 (* * * * *)"),
        Choice(value="0 * * * *", name="每小时整点 (0 * * * *)"),
        Choice(value="0 8 * * *", name="每天早上8点 (0 8 * * *)"),
        Choice(value="0 12 * * *", name="每天中午12点 (0 12 * * *)"),
        Choice(value="0 18 * * *", name="每天晚上6点 (0 18 * * *)"),
        Choice(value="0 9 * * 1", name="每周一早上9点 (0 9 * * 1)"),
        Choice(value="0 9 * * 1-5", name="工作日早上9点 (0 9 * * 1-5)"),
        Choice(value="0 0 1 * *", name="每月1号 (0 0 1 * *)"),
        Choice(value="custom", name="自定义"),
    ]

    selected = inquirer.select(message="选择 Cron 时间:", choices=choices).execute()

    if selected == "custom":
        return prompt_text("输入自定义 Cron 表达式 (分 时 日 月 周):")

    return selected


def prompt_channel_select() -> str:
    """Prompt user to select a channel type with status indicators.

    Displays all registered channels with their configuration status:
        - qqbot (已配置 ✓)
        - imessage (未配置 ○)

    Returns:
        The selected channel identifier string.

    Example:
        >>> channel = prompt_channel_select()
        # User sees list with status icons, selects one
        >>> print(channel)
        'qqbot'
    """
    choices = []

    # Build choices with status for each registered channel
    for channel_id in sorted(CHANNEL_REGISTRY.keys()):
        icon, status_text = get_channel_status(channel_id)
        # Format: "channel_name (status_text icon)"
        name = f"{channel_id} ({status_text} {icon})"
        choices.append(Choice(value=channel_id, name=name))

    return inquirer.select(
        message="选择通道类型:",
        choices=choices,
    ).execute()


def prompt_capture_channel_select() -> str:
    """Prompt user to select a capture-capable channel with status indicators.

    Filters CHANNEL_REGISTRY to only show channels where supports_capture is True.

    Returns:
        The selected channel identifier string.
    """
    from claw_cron.channels import get_channel

    choices = []
    for channel_id in sorted(CHANNEL_REGISTRY.keys()):
        ch = get_channel(channel_id)
        if not ch.supports_capture:
            continue
        icon, status_text = get_channel_status(channel_id)
        name = f"{channel_id} ({status_text} {icon})"
        choices.append(Choice(value=channel_id, name=name))

    if not choices:
        raise ValueError("没有支持 capture 的通道")

    return inquirer.select(
        message="选择通道类型:",
        choices=choices,
    ).execute()
