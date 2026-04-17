# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

import logging

import click

from claw_cron.__about__ import __version__
from claw_cron.cmd.add import add
from claw_cron.cmd.channels import channels
from claw_cron.cmd.chat import chat
from claw_cron.cmd.context import context
from claw_cron.cmd.command import command
from claw_cron.cmd.config import config
from claw_cron.cmd.delete import delete
from claw_cron.cmd.list import list_tasks
from claw_cron.cmd.log import log
from claw_cron.cmd.remind import remind
from claw_cron.cmd.run import run
from claw_cron.cmd.server import server


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-v", "--version")
def cli() -> None:
    """claw-cron: AI-powered cron task manager."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


cli.add_command(add)
cli.add_command(channels)
cli.add_command(context)
cli.add_command(command)
cli.add_command(list_tasks)
cli.add_command(delete)
cli.add_command(run)
cli.add_command(log)
cli.add_command(chat)
cli.add_command(server)
cli.add_command(config)
cli.add_command(remind)
