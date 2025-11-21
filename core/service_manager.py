"""Manage the Espanso service lifecycle for the GUI without leaking start/stop logic."""

from __future__ import annotations

import platform
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.cli_adapter import CLIAdapter


INSTALLER_URL = "https://github.com/federico-terzi/espanso/releases/latest/download/espanso-setup.exe"


def _download_installer(target: Path) -> Path:
    """Download the Espanso installer to a temporary location."""
    urllib.request.urlretrieve(INSTALLER_URL, target)
    return target


class ServiceManager:
    """Encapsulates Espanso CLI/service readiness so GUI bootstraps once."""

    def __init__(
        self,
        cli: CLIAdapter,
        status_attempts: int = 3,
        status_delay: float = 2.0,
        status_retry_window: float = 60.0,
    ) -> None:
        self._cli = cli
        self._status_attempts = max(1, status_attempts)
        self._status_delay = max(0.0, status_delay)
        self._status_retry_window = max(1.0, status_retry_window)
        self._service_ready = False
        self._install_attempted = False
        self._service_start_failed = False
        self._service_start_fail_time = 0.0
        self._handshake_steps: List[Tuple[str, Tuple[str, str]]] = []
        self._last_status_info: Optional[Dict[str, str]] = None

    def ensure_service_ready(self) -> List[Tuple[str, Tuple[str, str]]]:
        """Run the startup handshake once."""
        self._handshake_steps = [
            ("Ensure Espanso CLI", self.report_cli_status(start_if_missing=True)),
            ("Espanso service running", self.report_service_status(start_if_missing=True)),
        ]
        return self._handshake_steps

    def report_cli_status(self, start_if_missing: bool = False) -> Tuple[str, str]:
        try:
            result = self._cli.run(["--version"])
        except Exception as exc:
            return self._handle_cli_missing(exc, start_if_missing)

        if result.returncode == 0:
            return "success", result.stdout.strip() or "Espanso CLI ready"

        if start_if_missing:
            return self._install_cli(result.stderr or result.stdout)

        detail = result.stderr.strip() or result.stdout.strip() or "Espanso CLI unavailable"
        return "warning", detail

    def _handle_cli_missing(self, exc: Exception, start_if_missing: bool) -> Tuple[str, str]:
        message = str(exc) or "Espanso CLI missing"
        if not start_if_missing:
            return "error", message
        return self._install_cli(message)

    def _install_cli(self, detail: Optional[str] = None) -> Tuple[str, str]:
        if self._install_attempted:
            return "error", detail or "Espanso installer already attempted"
        self._install_attempted = True

        if platform.system() != "Windows":
            return "error", "Auto-install supported only on Windows"

        target = Path(tempfile.gettempdir()) / "espanso-setup.exe"
        try:
            installer = _download_installer(target)
        except Exception as exc:
            return "error", f"Failed to download installer: {exc}"

        try:
            result = subprocess.run(
                [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception as exc:
            return "error", f"Failed to launch installer: {exc}"

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
            return "error", f"Espanso installer failed: {error_msg}"

        return "success", f"Installer executed ({installer.name})"

    def report_service_status(self, start_if_missing: bool = False) -> Tuple[str, str]:
        try:
            status_result = self._cli.run(["status"])
            self._cache_status(status_result)
        except Exception as exc:
            return "error", str(exc)

        status_output = (status_result.stdout or status_result.stderr or "").strip()
        running = status_result.returncode == 0 and "running" in status_output.lower()

        if running:
            self._service_ready = True
            self._service_start_failed = False
            return "success", status_output or "Espanso running"

        if start_if_missing:
            return self._start_service()

        if self._service_start_failed and (time.time() - self._service_start_fail_time) < self._status_retry_window:
            return "warning", "Espanso service unavailable; start manually with 'espanso start'"

        detail = status_output or "Espanso service not running"
        return "warning", detail

    def _start_service(self) -> Tuple[str, str]:
        if self._service_ready:
            return "success", "Espanso daemon already running"

        now = time.time()
        if self._service_start_failed and (now - self._service_start_fail_time) < self._status_retry_window:
            return "warning", "Espanso service unavailable; start manually with 'espanso start'"

        try:
            self._cli.start_background(["start"])
        except Exception as exc:
            self._service_start_failed = True
            self._service_start_fail_time = now
            return "error", f"Failed to start Espanso: {exc}"

        if self._wait_for_status(self._status_attempts):
            self._service_ready = True
            self._service_start_failed = False
            return "success", "Espanso daemon started"

        self._service_start_failed = True
        self._service_start_fail_time = now
        return "error", "Service failed to start; run 'espanso start' manually"

    def _wait_for_status(self, attempts: int) -> bool:
        for index in range(attempts):
            if index > 0 and self._status_delay:
                time.sleep(self._status_delay)

            try:
                status_result = self._cli.run(["status"])
                self._cache_status(status_result)
            except Exception:
                continue

            status_output = (status_result.stdout or status_result.stderr or "").strip()
            if status_result.returncode == 0 and "running" in status_output.lower():
                return True
        return False

    def _cache_status(self, result: subprocess.CompletedProcess) -> None:
        self._last_status_info = {
            "returncode": result.returncode,
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
        }

    def get_status_snapshot(self) -> Dict[str, str]:
        if self._last_status_info:
            return self._last_status_info
        return {"returncode": 1, "stdout": "", "stderr": "Espanso status unavailable"}

    def should_skip_status_checks(self) -> bool:
        if not self._service_start_failed:
            return False
        return (time.time() - self._service_start_fail_time) < self._status_retry_window


"""
CHANGELOG
2025-11-21 Codex
- Added a dedicated `ServiceManager` to encapsulate Espanso installation/startup checks.
- Ensured the GUI runs a single handshake (install if missing, start if stopped) before allowing dashboard access.
- Added configurable retry/delay parameters and cached failure handling to avoid repeated spawn attempts.
2025-11-21 Codex
- Cached the last `espanso status` result so diagnostics reuse it instead of polling when the daemon is already known to be down.
- Added `should_skip_status_checks()`/`get_status_snapshot()` helpers so callers can avoid hitting the CLI while the service start failed within the retry window.
"""
