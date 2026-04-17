# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Abstract base class for message channels."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class MessageResult:
    """Result from a channel send operation.

    This dataclass standardizes the response format across different
    messaging channels, abstracting away platform-specific response structures.

    Attributes:
        success: Whether the message was sent successfully.
        message_id: Platform-specific message ID (if available).
        error: Error message if success is False.
        timestamp: Unix timestamp of send (if available).
        raw_response: Platform-specific raw response (for debugging).
    """

    success: bool
    message_id: str | None = None
    error: str | None = None
    timestamp: int | None = None
    raw_response: Any = None  # Platform-specific raw response


@dataclass
class ChannelConfig:
    """Base configuration for message channels.

    Subclasses should add channel-specific configuration fields.
    """

    enabled: bool = True


class MessageChannel(ABC):
    """Abstract base class for message channels.

    This class defines the interface that all message channels must implement.
    It provides a unified API for sending messages across different platforms
    (iMessage, QQ, Telegram, etc.).

    Subclasses must implement:
        - channel_id: Property returning unique channel identifier
        - send_text(): Send plain text message
        - send_markdown(): Send markdown-formatted message

    Optional methods:
        - send_template(): Send template-based message (raises NotImplementedError by default)
        - health_check(): Verify channel is operational (returns True by default)

    Example:
        >>> class IMessageChannel(MessageChannel):
        ...     @property
        ...     def channel_id(self) -> str:
        ...         return "imessage"
        ...
        ...     async def send_text(self, recipient: str, content: str) -> MessageResult:
        ...         # Implementation using macpymessenger
        ...         pass
    """

    def __init__(self, config: ChannelConfig | None = None) -> None:
        """Initialize the channel with optional configuration.

        Args:
            config: Channel configuration. Uses default if not provided.
        """
        self.config = config or ChannelConfig()

    @property
    @abstractmethod
    def channel_id(self) -> str:
        """Return unique channel identifier.

        This identifier is used in the channel registry and configuration.
        Examples: 'imessage', 'qq', 'telegram'.

        Returns:
            Channel identifier string.
        """
        ...

    @abstractmethod
    async def send_text(self, recipient: str, content: str) -> MessageResult:
        """Send a plain text message.

        Args:
            recipient: Recipient identifier (phone number, OpenID, user ID, etc.)
            content: Plain text message content.

        Returns:
            MessageResult indicating success or failure.

        Example:
            >>> result = await channel.send_text("+8613812345678", "Hello!")
        """
        ...

    @abstractmethod
    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        """Send a markdown-formatted message.

        For channels that don't support markdown (like iMessage),
        this should fall back to plain text.

        Args:
            recipient: Recipient identifier.
            content: Markdown-formatted message content.

        Returns:
            MessageResult indicating success or failure.
        """
        ...

    async def send_template(
        self,
        recipient: str,
        template_id: str,
        variables: dict[str, str],
    ) -> MessageResult:
        """Send a template-based message.

        This is an optional feature. Channels that don't support templates
        should raise NotImplementedError.

        Args:
            recipient: Recipient identifier.
            template_id: Template identifier.
            variables: Variables to substitute in the template.

        Returns:
            MessageResult indicating success or failure.

        Raises:
            NotImplementedError: If channel doesn't support templates.
        """
        raise NotImplementedError(
            f"{self.channel_id} does not support template messages"
        )

    async def health_check(self) -> bool:
        """Check if the channel is operational.

        Subclasses can override to perform platform-specific health checks.
        Default implementation returns True.

        Returns:
            True if channel is healthy, False otherwise.
        """
        return True

    @property
    def supports_capture(self) -> bool:
        """Whether this channel supports openid capture via WebSocket."""
        return False

    async def capture_openid(self, timeout: int = 300) -> str:
        """Capture user openid by waiting for an incoming message.

        Args:
            timeout: Timeout in seconds (default: 300s / 5 min).

        Returns:
            Captured openid string.

        Raises:
            NotImplementedError: If channel doesn't support capture.
            ChannelConfigError: If channel is not configured.
            ChannelError: If capture fails or times out.
        """
        raise NotImplementedError(
            f"{self.channel_id} does not support capture"
        )

    def get_channel_name(self) -> str:
        """Return channel name for logging/debugging.

        Extracts the channel name from the class name by removing
        the "Channel" suffix and converting to lowercase.

        Returns:
            Channel name (e.g., "imessage", "qqbot").
        """
        return self.__class__.__name__.replace("Channel", "").lower()
