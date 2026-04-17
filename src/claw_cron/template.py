# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Template rendering for {{ }} syntax used in script and message fields."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def render(template: str, context: dict[str, Any] | None = None) -> str:
    """Render a template string with variables.

    Supported variables:
        {{ date }}              -> Current date in YYYY-MM-DD format
        {{ time }}              -> Current time in HH:MM:SS format
        {{ context.KEY }}       -> Value from context dict under key KEY

    Unknown variables are left as-is.

    Args:
        template: Template string with {{ }} placeholders.
        context: Optional context dict for {{ context.xxx }} variables.

    Returns:
        Rendered string with variables replaced.
    """
    now = datetime.now()
    builtins: dict[str, str] = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
    }

    def replace(match: re.Match) -> str:
        key = match.group(1).strip()
        if key in builtins:
            return builtins[key]
        if key.startswith("context.") and context is not None:
            ctx_key = key[len("context."):]
            val = context.get(ctx_key)
            if val is not None:
                return str(val)
        return match.group(0)  # leave unknown variables as-is

    return re.sub(r"\{\{\s*(\S+)\s*\}\}", replace, template)
