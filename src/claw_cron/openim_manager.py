# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""OpenIM subprocess lifecycle manager for claw-cron.

Manages the OpenIM Rust server as a child process, providing:
- Port availability check
- Process start / stop / ensure-running
- PID file tracking
- Cleanup of stale processes

Usage:
    from claw_cron.openim_manager import OpenIMProcessManager

    # Server mode: start on boot, stop on shutdown
    OpenIMProcessManager.start()
    ...
    OpenIMProcessManager.stop()

    # On-demand mode: ensure running, auto-stop if we started it
    we_started = OpenIMProcessManager.ensure_running()
    ... send message ...
    if we_started:
        OpenIMProcessManager.stop()
"""

from __future__ import annotations

import contextlib
import os
import signal
import socket
import subprocess
import time
from pathlib import Path

from claw_cron.config import load_config

OPENIM_PID_FILE = Path.home() / ".config" / "claw-cron" / "openim.pid"


def _get_openim_config() -> dict:
    """Load openim-specific config from config.yaml with defaults."""
    cfg = load_config()
    openim_cfg = cfg.get("openim", {})
    return {
        "uri": openim_cfg.get("uri", "ws://127.0.0.1:12702/ws"),
        "port": openim_cfg.get("port", 12702),
        "openim_bin": openim_cfg.get("openim_bin", "openim"),
        "config_path": openim_cfg.get(
            "config_path", str(Path.home() / ".config" / "claw-cron" / "openim.yml")
        ),
    }


def _port_is_open(port: int) -> bool:
    """Check if localhost port is accepting connections."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def _find_pid_by_port(port: int) -> int | None:
    """Find PID listening on a given port using lsof."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().splitlines()[0])
    except (OSError, ValueError):
        pass
    return None


def _kill_pid(pid: int, sig: int = signal.SIGTERM) -> None:
    """Send signal to a process, ignoring errors."""
    with contextlib.suppress(OSError, ProcessLookupError):
        os.kill(pid, sig)


def _wait_for_port(port: int, timeout: float = 10.0) -> bool:
    """Poll until port is open or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_is_open(port):
            return True
        time.sleep(0.2)
    return False


class OpenIMProcessManager:
    """Manage the OpenIM server child process."""

    @staticmethod
    def is_running(port: int | None = None) -> bool:
        """Return True if openim is accepting connections on the given port."""
        cfg = _get_openim_config()
        port = port if port is not None else cfg["port"]
        return _port_is_open(port)

    @staticmethod
    def start(
        port: int | None = None,
        config_path: str | None = None,
        openim_bin: str | None = None,
    ) -> subprocess.Popen | None:
        """Start the openim server subprocess.

        Returns the Popen object on success, None if already running.
        """
        cfg = _get_openim_config()
        port = port if port is not None else cfg["port"]
        config_path = config_path if config_path is not None else cfg["config_path"]
        openim_bin = openim_bin if openim_bin is not None else cfg["openim_bin"]

        if _port_is_open(port):
            # Already running — reuse
            return None

        # Ensure config file exists
        cfg_path = Path(config_path).expanduser()
        if not cfg_path.exists():
            raise FileNotFoundError(
                f"OpenIM config not found: {cfg_path}. "
                "Please create it with your platform credentials."
            )

        OPENIM_PID_FILE.parent.mkdir(parents=True, exist_ok=True)

        # OpenIM reads config from ~/.config/openim/config.yml only.
        # Sync our openim.yml to OpenIM's config path before starting.
        openim_config_dir = Path.home() / ".config" / "openim"
        openim_config_dir.mkdir(parents=True, exist_ok=True)
        openim_default_config = openim_config_dir / "config.yml"

        import shutil

        shutil.copy2(str(cfg_path), str(openim_default_config))

        proc = subprocess.Popen(
            [openim_bin, "server", "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait for port to open
        if not _wait_for_port(port, timeout=10.0):
            proc.terminate()
            proc.wait(timeout=5)
            raise RuntimeError(f"OpenIM server did not start on port {port} within 10s")

        OPENIM_PID_FILE.write_text(str(proc.pid))
        return proc

    @staticmethod
    def stop(port: int | None = None) -> None:
        """Stop the openim server subprocess gracefully."""
        cfg = _get_openim_config()
        port = port if port is not None else cfg["port"]

        # Try PID file first
        pid: int | None = None
        if OPENIM_PID_FILE.exists():
            with contextlib.suppress(ValueError, OSError):
                pid = int(OPENIM_PID_FILE.read_text().strip())

        if pid is not None:
            _kill_pid(pid, signal.SIGTERM)
            # Wait up to 5s
            for _ in range(50):
                try:
                    os.kill(pid, 0)
                except (OSError, ProcessLookupError):
                    break
                time.sleep(0.1)
            else:
                _kill_pid(pid, signal.SIGKILL)

        # Fallback: kill any process on the port
        fallback_pid = _find_pid_by_port(port)
        if fallback_pid is not None and fallback_pid != pid:
            _kill_pid(fallback_pid, signal.SIGTERM)
            time.sleep(0.5)
            try:
                os.kill(fallback_pid, 0)
            except (OSError, ProcessLookupError):
                pass
            else:
                _kill_pid(fallback_pid, signal.SIGKILL)

        OPENIM_PID_FILE.unlink(missing_ok=True)

    @staticmethod
    def ensure_running(
        port: int | None = None,
        config_path: str | None = None,
        openim_bin: str | None = None,
    ) -> bool:
        """Ensure openim is running; start it if not.

        Returns True if this call started the process (caller should stop it).
        Returns False if it was already running (caller should NOT stop it).
        """
        cfg = _get_openim_config()
        port = port if port is not None else cfg["port"]

        if _port_is_open(port):
            return False

        OpenIMProcessManager.start(port, config_path, openim_bin)
        return True
