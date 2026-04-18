# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Tool abstraction for provider-agnostic function calling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolDefinition:
    """Provider-agnostic tool definition.

    This dataclass defines a tool in a neutral format that can be
    converted to provider-specific formats (Anthropic, OpenAI, etc.).

    Attributes:
        name: Tool name (must be unique within a conversation).
        description: Human-readable description of what the tool does.
        parameters: JSON Schema object defining the input parameters.
    """

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema format


@dataclass
class ToolCall:
    """Provider-agnostic tool call result.

    When a model decides to call a tool, this dataclass captures the
    call details in a normalized format.

    Attributes:
        id: Tool call ID (for response correlation).
        name: Name of the tool being called.
        arguments: Parsed arguments as a dictionary.
    """

    id: str
    name: str
    arguments: dict[str, Any]


def to_anthropic_tool(tool: ToolDefinition) -> dict[str, Any]:
    """Convert ToolDefinition to Anthropic ToolParam format.

    Anthropic uses 'input_schema' instead of 'parameters'.

    Args:
        tool: Provider-agnostic tool definition.

    Returns:
        Anthropic-compatible tool dictionary.

    Example:
        >>> tool = ToolDefinition(
        ...     name="create_task",
        ...     description="Create a scheduled task",
        ...     parameters={"type": "object", "properties": {"name": {"type": "string"}}}
        ... )
        >>> anthropic_tool = to_anthropic_tool(tool)
        >>> "input_schema" in anthropic_tool
        True
    """
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.parameters,
    }


def to_openai_tool(tool: ToolDefinition) -> dict[str, Any]:
    """Convert ToolDefinition to OpenAI function format.

    OpenAI wraps tools in a 'function' object with 'parameters' key.

    Args:
        tool: Provider-agnostic tool definition.

    Returns:
        OpenAI-compatible tool dictionary.

    Example:
        >>> tool = ToolDefinition(
        ...     name="create_task",
        ...     description="Create a scheduled task",
        ...     parameters={"type": "object", "properties": {"name": {"type": "string"}}}
        ... )
        >>> openai_tool = to_openai_tool(tool)
        >>> openai_tool["type"]
        'function'
        >>> "parameters" in openai_tool["function"]
        True
    """
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


def to_codebuddy_tool(tool: ToolDefinition) -> dict[str, Any]:
    """Convert ToolDefinition to Codebuddy SDK tool format.

    Codebuddy SDK uses simple type mapping or JSON Schema for parameters.
    This function preserves the JSON Schema format from ToolDefinition.

    Args:
        tool: Provider-agnostic tool definition.

    Returns:
        Dictionary compatible with Codebuddy SDK @tool decorator.

    Example:
        >>> tool = ToolDefinition(
        ...     name="create_task",
        ...     description="Create a scheduled task",
        ...     parameters={"type": "object", "properties": {"name": {"type": "string"}}}
        ... )
        >>> cb_tool = to_codebuddy_tool(tool)
        >>> cb_tool["name"]
        'create_task'
        >>> "parameters" in cb_tool
        True
    """
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters,
    }
