# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

import click

from claw_cron.__about__ import __version__


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-v", "--version")
def cli() -> None:
    """claw-cron: AI-powered cron task manager."""
    pass
