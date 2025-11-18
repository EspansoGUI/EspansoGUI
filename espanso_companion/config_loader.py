"""Config discovery helpers for Espanso Companion Pro."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple


@dataclass
class ConfigPaths:
    config: Path
    match: Path
    packages: Path
    runtime: Path


class ConfigLoader:
    """Auto-detects Espanso directories with CLI and env fallbacks."""

    def __init__(self, runner: Callable = subprocess.run):
        self._runner = runner
        self._last_cli_paths: Dict[str, Path] = {}
        self._last_env_paths: Dict[str, Path] = {}

    def discover_paths(self, config_override: Optional[Path] = None) -> ConfigPaths:
        """Return official workspace paths across platforms."""
        sys_name = platform.system()
        env_overrides = self._env_paths()
        self._last_env_paths = env_overrides.copy()
        detected = self._probe_cli_paths()
        self._last_cli_paths = detected.copy()

        override_path: Optional[Path] = None
        if config_override:
            override_path = config_override
        elif env_overrides.get("config"):
            override_path = env_overrides["config"]

        config = override_path or detected.get("config") or self._default_config_path(sys_name)
        match = detected.get("match") or config / "match"
        packages = env_overrides.get("packages") or detected.get("packages") or config.parent / "packages"
        runtime = env_overrides.get("runtime") or detected.get("runtime") or config.parent / "run"

        return ConfigPaths(
            config=config,
            match=match,
            packages=packages,
            runtime=runtime,
        )

    def _probe_cli_paths(self) -> Dict[str, Path]:
        """Probe espanso CLI for paths with Windows .cmd -> .exe resolution."""
        result: Dict[str, Path] = {}
        try:
            # Find the actual executable (handles Windows .cmd wrapper issue)
            espanso_exe, use_cmd_wrapper = self._find_espanso_executable()
            command: List[str] = [espanso_exe, "path"]
            if use_cmd_wrapper:
                command = ["cmd", "/c", *command]
            completed = self._runner(
                command,
                capture_output=True,
                text=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
            # Log the error but continue with fallback paths
            # This is intentional - we don't want to fail initialization
            return result

        for line in completed.stdout.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            result[key] = Path(value.strip())
        return result

    def _find_espanso_executable(self) -> Tuple[str, bool]:
        """
        Find the actual espanso executable.

        On Windows, shutil.which() returns espanso.cmd, but subprocess.run()
        needs the actual .exe file for reliable output capture.
        """
        espanso_path = shutil.which("espanso")

        if not espanso_path:
            raise FileNotFoundError("espanso not found in PATH")

        if platform.system() == "Windows":
            lower = espanso_path.lower()
            base_dir = Path(espanso_path).parent
            if lower.endswith("espansod.exe"):
                exe_candidate = base_dir / "espanso.exe"
                if exe_candidate.exists():
                    return str(exe_candidate), False
                cmd_candidate = base_dir / "espanso.cmd"
                if cmd_candidate.exists():
                    return str(cmd_candidate), True
                raise FileNotFoundError("espanso CLI wrapper not found; run 'espanso env-path add'")
            if lower.endswith(".cmd"):
                return espanso_path, True
            if lower.endswith("espanso.exe"):
                return espanso_path, False

        return espanso_path, False

    def _default_config_path(self, sys_name: str) -> Path:
        """Fallback for each OS plus environment overrides."""
        env_override = self._env_paths()
        if env_override.get("config"):
            return env_override["config"]
        if sys_name == "Linux":
            return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "espanso"
        if sys_name == "Darwin":
            return Path.home() / "Library" / "Application Support" / "espanso"
        if sys_name == "Windows":
            return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "espanso"
        raise RuntimeError("Unsupported platform")

    @staticmethod
    def _env_paths() -> Dict[str, Path]:
        mapping = {
            "ESPANSO_CONFIG_DIR": "config",
            "ESPANSO_RUNTIME_DIR": "runtime",
            "ESPANSO_PACKAGE_DIR": "packages",
        }
        result: Dict[str, Path] = {}
        for env_key, label in mapping.items():
            value = os.environ.get(env_key)
            if value:
                result[label] = Path(value).expanduser()
        return result

    @staticmethod
    def resolve_env_paths(paths: Iterable[Path]) -> Dict[str, Path]:
        """Ensure each path exists; create directories lazily."""
        resolved = {}
        for path in paths:
            resolved[str(path)] = path
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
        return resolved

    def last_cli_paths(self) -> Dict[str, Path]:
        return self._last_cli_paths

    def last_env_paths(self) -> Dict[str, Path]:
        return self._last_env_paths


"""
CHANGELOG
2025-11-14 Codex
- Added config override plumbing, persisted CLI/env metadata, and canonical env variable resolution.
2025-11-14 Codex
- Adjusted Windows CLI detection to favor espanso.exe so config overrides work with espanso's global flags.
2025-11-14 Codex
- Simplified detection to allow daemon-only installs while still supporting cmd wrappers.
"""
