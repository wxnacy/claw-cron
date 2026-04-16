# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

import click

from claw_cron.__about__ import __version__
from claw_cron.cmd.delete import delete
from claw_cron.cmd.list import list_tasks


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-v", "--version")
def cli() -> None:
    """claw-cron: AI-powered cron task manager."""
    pass


cli.add_command(list_tasks)
cli.add_command(delete)
