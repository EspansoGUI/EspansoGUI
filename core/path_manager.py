from __future__ import annotations

from typing import Optional, Any, Dict
from pathlib import Path
from espanso_companion.config_loader import ConfigLoader


class PathManager:
    """Wrapper around ConfigLoader.discover_paths to provide a test seam and explicit API.

    Accepts an optional `loader` for injection in tests.
    """

    def __init__(self, loader: Optional[Any] = None, override: Optional[str] = None) -> None:
        self.loader = loader or ConfigLoader()
        self._paths = None
        if override is not None:
            self.discover_paths(override)
        else:
            # discover immediately with no override for simple usage
            try:
                self._paths = self.loader.discover_paths(None)
            except Exception:
                self._paths = None

    def discover_paths(self, override: Optional[str] = None) -> Any:
        self._paths = self.loader.discover_paths(override)
        return self._paths

    def get_paths(self) -> Any:
        return self._paths

    def set_override(self, override: Optional[str]) -> None:
        self.discover_paths(override)

    def last_env_paths(self) -> Dict[str, Path]:
        """Expose the last-detected environment overrides."""
        return self.loader.last_env_paths()

    def last_cli_paths(self) -> Dict[str, Path]:
        """Expose the last CLI-discovered paths for diagnostics."""
        return self.loader.last_cli_paths()
