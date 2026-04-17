# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""When condition expression evaluator for conditional notifications."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Pattern: key (==|!=) value
_EXPR_RE = re.compile(r"^\s*(\w+)\s*(==|!=)\s*(.+?)\s*$")


def _coerce(value: str) -> bool | str | int | float:
    """Coerce string literal to Python type.

    - "true" / "false" -> bool
    - integer string -> int
    - float string -> float
    - otherwise -> str (strip surrounding quotes)
    """
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    # Strip surrounding single or double quotes
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def evaluate_when(when: str | None, context: dict) -> bool:
    """Evaluate a when expression against a context dict.

    Supports == and != operators only.
    On parse error or missing key, logs a warning and returns True
    (conservative: send notification rather than silently suppress).

    Args:
        when: Expression string like 'signed_in == false' or None.
        context: Task context dict (merged, from executor).

    Returns:
        True if notification should be sent, False if suppressed.
    """
    if not when:
        return True

    m = _EXPR_RE.match(when)
    if not m:
        logger.warning(
            "when expression %r could not be parsed — sending notification", when
        )
        return True

    key, op, raw_value = m.group(1), m.group(2), m.group(3)

    if key not in context:
        logger.warning(
            "when expression %r: key %r not found in context — sending notification",
            when,
            key,
        )
        return True

    ctx_val = context[key]
    expr_val = _coerce(raw_value)

    try:
        if op == "==":
            result = ctx_val == expr_val
        else:  # !=
            result = ctx_val != expr_val
    except Exception:
        logger.warning(
            "when expression %r: comparison failed — sending notification", when
        )
        return True

    if not result:
        logger.info("Notification suppressed: when condition %r not met", when)
    return result
