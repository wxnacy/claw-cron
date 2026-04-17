# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Email channel implementation for claw-cron.

Supports plain text, Markdown→HTML, and file attachments via aiosmtplib.

Environment Variables:
    CLAW_CRON_EMAIL_HOST: SMTP server host
    CLAW_CRON_EMAIL_PORT: SMTP port (default: 587)
    CLAW_CRON_EMAIL_USERNAME: SMTP username
    CLAW_CRON_EMAIL_PASSWORD: SMTP password
    CLAW_CRON_EMAIL_FROM_EMAIL: Sender email address
    CLAW_CRON_EMAIL_USE_TLS: Use STARTTLS (default: true)
"""

from __future__ import annotations

import aiosmtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

from .base import ChannelConfig, MessageChannel, MessageResult
from .exceptions import ChannelAuthError, ChannelConfigError


class EmailConfig(BaseSettings, ChannelConfig):
    """Configuration for Email channel.

    Attributes:
        host: SMTP server host.
        port: SMTP port (default 587).
        username: SMTP username.
        password: SMTP password.
        from_email: Sender email address.
        use_tls: Use STARTTLS (default True).
    """

    host: str | None = Field(default=None, description="SMTP server host")
    port: int = Field(default=587, description="SMTP port")
    username: str | None = Field(default=None, description="SMTP username")
    password: str | None = Field(default=None, description="SMTP password")
    from_email: str | None = Field(default=None, description="Sender email address")
    use_tls: bool = Field(default=True, description="Use STARTTLS")

    class Config:
        env_prefix = "CLAW_CRON_EMAIL_"
        env_file = ".env"
        extra = "ignore"


class EmailChannel(MessageChannel):
    """Email channel implementation using aiosmtplib.

    Supports plain text, Markdown→HTML (multipart/alternative), and attachments.

    Example:
        >>> channel = EmailChannel()
        >>> result = await channel.send_text("user@example.com", "Hello!")
    """

    def __init__(self, config: EmailConfig | dict | None = None) -> None:
        if config is None:
            config_obj = EmailConfig()
        elif isinstance(config, dict):
            config_obj = EmailConfig(**config)
        else:
            config_obj = config
        super().__init__(config_obj)

    @property
    def channel_id(self) -> str:
        return "email"

    def _validate_config(self) -> None:
        """Validate required SMTP fields.

        Raises:
            ChannelConfigError: If any required field is missing.
        """
        for field in ("host", "username", "password", "from_email"):
            if not getattr(self.config, field, None):
                raise ChannelConfigError(
                    f"Email {field} is required. Set CLAW_CRON_EMAIL_{field.upper()} environment variable.",
                    channel_id=self.channel_id,
                )

    async def _smtp_send(self, msg: MIMEText | MIMEMultipart) -> MessageResult:
        """Send a pre-built MIME message via SMTP."""
        try:
            await aiosmtplib.send(
                msg,
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                start_tls=self.config.use_tls,
            )
            return MessageResult(success=True)
        except aiosmtplib.SMTPAuthenticationError as e:
            raise ChannelAuthError(str(e), channel_id=self.channel_id)
        except aiosmtplib.SMTPException as e:
            return MessageResult(success=False, error=str(e))

    async def send_text(
        self,
        recipient: str,
        content: str,
        attachments: list[str] | None = None,
    ) -> MessageResult:
        """Send a plain text email, optionally with file attachments.

        Args:
            recipient: Comma-separated recipient email address(es).
            content: Plain text message content.
            attachments: Optional list of file paths to attach.

        Returns:
            MessageResult indicating success or failure.
        """
        self._validate_config()
        recipients = [r.strip() for r in recipient.split(",")]

        if attachments:
            msg: MIMEText | MIMEMultipart = MIMEMultipart()
            msg.attach(MIMEText(content, "plain", "utf-8"))
            for path in attachments:
                with open(path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={Path(path).name}",
                )
                msg.attach(part)
        else:
            msg = MIMEText(content, "plain", "utf-8")

        msg["Subject"] = content[:50]
        msg["From"] = self.config.from_email
        msg["To"] = ", ".join(recipients)

        return await self._smtp_send(msg)

    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        """Send a Markdown email as multipart/alternative (plain + HTML).

        Args:
            recipient: Comma-separated recipient email address(es).
            content: Markdown-formatted message content.

        Returns:
            MessageResult indicating success or failure.
        """
        self._validate_config()
        import markdown as md_lib

        recipients = [r.strip() for r in recipient.split(",")]
        html_content = md_lib.markdown(content)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = content.split("\n")[0].lstrip("# ")[:50]
        msg["From"] = self.config.from_email
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        return await self._smtp_send(msg)
