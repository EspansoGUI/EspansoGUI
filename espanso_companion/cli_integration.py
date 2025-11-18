"""CLI wrappers for Espanso commands consumed by the backend."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


class EspansoCLI:
    """Encapsulates espanso CLI commands for reuse in Streamlit."""

    def __init__(self, runner: Callable = subprocess.run, timeout: Optional[int] = 60):
        self._runner = runner
        self.timeout = timeout
        self._espanso_exe: Optional[str] = None  # Cache for espanso executable path
        self._config_dir: Optional[Path] = None
        self._command_prefix: List[str] = []

    def _find_espanso_executable(self) -> str:
        """
        Find the actual espanso executable.

        On Windows, shutil.which() returns espanso.cmd, but subprocess.run()
        cannot execute .cmd files without shell=True, and shell=True doesn't
        properly capture output. We need to find espansod.exe directly.
        """
        if self._espanso_exe:
            return self._espanso_exe

        espanso_path = shutil.which("espanso")

        if not espanso_path:
            raise FileNotFoundError("espanso not found in PATH")

        self._command_prefix = []

        if platform.system() == "Windows":
            lower_path = espanso_path.lower()
            base_dir = Path(espanso_path).parent
            if lower_path.endswith("espansod.exe"):
                exe_candidate = base_dir / "espanso.exe"
                if exe_candidate.exists():
                    self._espanso_exe = str(exe_candidate)
                    return self._espanso_exe
                cmd_candidate = base_dir / "espanso.cmd"
                if cmd_candidate.exists():
                    self._command_prefix = ["cmd", "/c"]
                    self._espanso_exe = str(cmd_candidate)
                    return self._espanso_exe
                raise FileNotFoundError("espanso CLI wrapper not found; run 'espanso env-path add'")
            if lower_path.endswith(".cmd"):
                self._command_prefix = ["cmd", "/c"]
                self._espanso_exe = espanso_path
                return self._espanso_exe
            if lower_path.endswith("espanso.exe"):
                self._espanso_exe = espanso_path
                return self._espanso_exe

        self._espanso_exe = espanso_path
        return self._espanso_exe

    def run(
        self,
        args: Sequence[str],
        cwd: Optional[Path] = None,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a command and return the CompletedProcess for inspection."""
        try:
            # Get the actual executable path (handles Windows .cmd -> .exe resolution)
            espanso_exe = self._find_espanso_executable()
            cmd = [*self._command_prefix, espanso_exe, *args]

            env = None
            if self._config_dir:
                env = os.environ.copy()
                env["ESPANSO_CONFIG_DIR"] = str(self._config_dir)

            # Run directly without shell - works cross-platform
            result = self._runner(
                cmd,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                check=False,
                timeout=self.timeout,
                env=env,
            )

            return result
        except FileNotFoundError as exc:
            return CompletedProcess(
                ["espanso", *args],
                returncode=1,
                stdout="",
                stderr=f"espanso not found: {exc}"
            )
        except subprocess.TimeoutExpired as exc:
            # Timeout errors should be caught and reported properly
            return CompletedProcess(
                ["espanso", *args],
                returncode=124,  # Standard timeout exit code
                stdout="",
                stderr=f"Command timed out after {self.timeout} seconds: {exc}"
            )

    def status(self) -> Dict[str, Any]:
        """Return parsed output for `espanso status` to show install/daemon info."""
        result = self.run(["status"])
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }

    def packages(self) -> List[Dict[str, Any]]:
        """List packages via the CLI; return parsed JSON if available."""
        result = self.run(["package", "list"])
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return [{"raw": result.stdout.strip()}]

    def install_package(self, name: str) -> subprocess.CompletedProcess:
        return self.run(["package", "install", name])

    def uninstall_package(self, name: str) -> subprocess.CompletedProcess:
        return self.run(["package", "uninstall", name])

    def reload(self) -> subprocess.CompletedProcess:
        return self.run(["restart"])

    def path(self) -> Dict[str, Path]:
        """Get Espanso paths with proper validation and error handling."""
        result = self.run(["path"])

        # Check if command failed
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to get espanso paths (exit code {result.returncode}): "
                f"{result.stderr.strip() or result.stdout.strip() or 'Unknown error'}"
            )

        mapping = {}
        for line in result.stdout.splitlines():
            if ":" not in line:
                continue  # Skip malformed lines
            key, value = line.split(":", 1)
            mapping[key.strip().lower()] = Path(value.strip())

        # Validate that required paths are present
        required_keys = {"config", "packages", "runtime"}
        missing = required_keys - set(mapping.keys())
        if missing:
            raise RuntimeError(
                f"Espanso path command did not return required paths: {', '.join(missing)}. "
                f"Got: {', '.join(mapping.keys())}"
            )

        return mapping

    def set_config_dir(self, config_dir: Path) -> None:
        self._config_dir = config_dir

def synthesize_conversation(commands: Iterable[Tuple[str, Sequence[str]]]) -> List[Dict[str, Any]]:
    """Utility for building CLI timeline data, useful for analytics wiring."""
    history = []
    for label, args in commands:
        history.append({"label": label, "args": args})
    return history


"""
CHANGELOG
2025-11-14 Codex
- Added --config-dir injection and setter so CLI invocations honor custom workspace roots.
2025-11-14 Codex
- Updated Windows resolution to prefer espanso.exe over espansod.exe to avoid UnknownArgument errors.
2025-11-14 Codex
- Reinstated environment-driven config overrides and wrapper support to prevent regressions on daemon-only installs.
"""
