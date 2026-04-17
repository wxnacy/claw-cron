# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Context CLI commands — get and set task context for AI agent use."""

from __future__ import annotations

import json

import click

from claw_cron.context import load_context, save_context


@click.group()
def context() -> None:
    """Manage task context (for AI agent use)."""


@context.command("get")
@click.argument("task_name")
def context_get(task_name: str) -> None:
    """Print task context as JSON.

    Outputs the full context JSON for TASK_NAME to stdout.
    AI agents can call this via subprocess to read task state.

    Example:
        claw-cron context get my_task
    """
    ctx = load_context(task_name)
    click.echo(json.dumps(ctx, ensure_ascii=False, indent=2))


@context.command("set")
@click.argument("task_name")
@click.option("--key", required=True, help="Context key to set.")
@click.option("--value", required=True, help="Value to set (string).")
def context_set(task_name: str, key: str, value: str) -> None:
    """Set a key-value pair in task context.

    AI agents can call this via subprocess to write task state.

    Example:
        claw-cron context set my_task --key signed_in --value true
    """
    ctx = load_context(task_name)
    ctx[key] = value
    save_context(task_name, ctx)
    click.echo(f"Set {key}={value} for task '{task_name}'")
