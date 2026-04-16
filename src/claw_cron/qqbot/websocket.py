# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""QQ Bot WebSocket client implementation.

This module provides a WebSocket client for connecting to QQ Bot Gateway,
handling heartbeat, reconnection, and message event dispatching.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Awaitable, Callable

import httpx
import websockets
from websockets.asyncio.client import ClientConnection

from .events import C2CMessage, EventType, OpCode, parse_c2c_message


@dataclass
class GatewayConfig:
    """Configuration for QQ Bot Gateway connection.

    Attributes:
        app_id: QQ Bot App ID.
        access_token: OAuth2 access token.
        intents: Event subscription bitflags (default: C2C_MESSAGE_CREATE).
    """

    app_id: str
    access_token: str
    intents: int = 1 << 25  # C2C_MESSAGE_CREATE intent


class QQBotWebSocket:
    """WebSocket client for QQ Bot Gateway.

    Handles connection lifecycle including:
    - Hello handshake and heartbeat setup
    - Identify/Resume authentication
    - Automatic heartbeat sending
    - Message event dispatching
    - Graceful reconnection

    Attributes:
        config: Gateway configuration.
        ws: WebSocket connection (None when disconnected).
        heartbeat_interval: Heartbeat interval in milliseconds.
        session_id: Session ID for resume.
        seq: Last received sequence number.
        on_c2c_message: Callback for C2C message events.
    """

    def __init__(self, config: GatewayConfig) -> None:
        """Initialize WebSocket client.

        Args:
            config: Gateway configuration with app_id and access_token.
        """
        self.config = config
        self.ws: ClientConnection | None = None
        self.heartbeat_interval: int = 45000  # Default 45 seconds
        self.session_id: str | None = None
        self.seq: int | None = None
        self._running = False
        self.on_c2c_message: Callable[[C2CMessage], Awaitable[None]] | None = None

    async def get_gateway_url(self) -> str:
        """Fetch WebSocket gateway URL from QQ Bot API.

        Returns:
            WebSocket URL (e.g., "wss://api.sgroup.qq.com/websocket/").

        Raises:
            httpx.HTTPStatusError: If API request fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.sgroup.qq.com/gateway",
                headers={"Authorization": f"QQBot {self.config.access_token}"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["url"]

    async def connect(self, gateway_url: str | None = None) -> None:
        """Connect to QQ Bot Gateway.

        Args:
            gateway_url: WebSocket URL. If None, fetches from API.
        """
        if gateway_url is None:
            gateway_url = await self.get_gateway_url()

        self._running = True
        await self._connection_loop(gateway_url)

    async def _connection_loop(self, gateway_url: str) -> None:
        """Main connection loop with reconnection support."""
        retry_count = 0
        max_retries = 5
        base_delay = 1

        while self._running and retry_count < max_retries:
            try:
                async with websockets.connect(
                    gateway_url,
                    ping_interval=None,  # Use QQ protocol heartbeat
                    ping_timeout=None,
                ) as ws:
                    self.ws = ws
                    retry_count = 0  # Reset on successful connection
                    await self._receive_loop()
            except Exception as e:
                retry_count += 1
                delay = base_delay * (2 ** (retry_count - 1))
                print(f"Connection lost: {e}. Retrying in {delay}s ({retry_count}/{max_retries})")
                await asyncio.sleep(delay)

    async def _receive_loop(self) -> None:
        """Receive and process messages from Gateway."""
        heartbeat_task: asyncio.Task[None] | None = None

        try:
            async for message in self.ws:
                data = json.loads(message)
                op = data.get("op")
                self.seq = data.get("s")

                if op == OpCode.HELLO.value:
                    # Server hello - setup heartbeat and identify
                    self.heartbeat_interval = data["d"]["heartbeat_interval"]
                    heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                    # Resume or Identify
                    if self.session_id and self.seq:
                        await self._resume()
                    else:
                        await self._identify()

                elif op == OpCode.DISPATCH.value:
                    event_type = data.get("t")
                    if event_type == EventType.READY.value:
                        self.session_id = data["d"]["session_id"]
                        print("✓ Session established")
                    elif event_type == EventType.RESUMED.value:
                        print("✓ Session resumed")
                    elif event_type == EventType.C2C_MESSAGE_CREATE.value:
                        await self._handle_c2c_message(data["d"])

                elif op == OpCode.HEARTBEAT_ACK.value:
                    pass  # Heartbeat ACK, no action needed

        finally:
            if heartbeat_task:
                heartbeat_task.cancel()

    async def _heartbeat_loop(self) -> None:
        """Send heartbeat at configured interval."""
        while self._running:
            await asyncio.sleep(self.heartbeat_interval / 1000)
            if self.ws and self.seq is not None:
                await self.ws.send(json.dumps({
                    "op": OpCode.HEARTBEAT.value,
                    "d": self.seq
                }))

    async def _identify(self) -> None:
        """Send Identify payload to establish new session."""
        if self.ws is None:
            return
        await self.ws.send(json.dumps({
            "op": OpCode.IDENTIFY.value,
            "d": {
                "token": f"Bot {self.config.app_id}.{self.config.access_token}",
                "intents": self.config.intents,
                "shard": [0, 1],
                "properties": {}
            }
        }))

    async def _resume(self) -> None:
        """Send Resume payload to restore previous session."""
        if self.ws is None:
            return
        await self.ws.send(json.dumps({
            "op": OpCode.RESUME.value,
            "d": {
                "token": f"Bot {self.config.app_id}.{self.config.access_token}",
                "session_id": self.session_id,
                "seq": self.seq
            }
        }))

    async def _handle_c2c_message(self, event_data: dict) -> None:
        """Handle C2C_MESSAGE_CREATE event."""
        message = parse_c2c_message(event_data)
        print(f"📩 Message from {message.openid}: {message.content}")

        if self.on_c2c_message:
            await self.on_c2c_message(message)

    async def close(self) -> None:
        """Close the WebSocket connection gracefully."""
        self._running = False
        if self.ws:
            await self.ws.close()
