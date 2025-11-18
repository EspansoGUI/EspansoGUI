"""Cross-platform helpers for Espanso Companion."""

from __future__ import annotations

import platform
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class PlatformInfo:
    """Summarizes runtime platform details in one place."""

    system: str

    @property
    def is_windows(self) -> bool:
        return self.system == "windows"

    @property
    def is_macos(self) -> bool:
        return self.system == "darwin"

    @property
    def is_linux(self) -> bool:
        return self.system == "linux"

    @property
    def is_wsl(self) -> bool:
        if not self.is_linux:
            return False
        release = platform.release().lower()
        if "microsoft" in release or "wsl" in release:
            return True
        return bool(os.environ.get("WSL_DISTRO_NAME"))

    def gui_preferences(self) -> List[Optional[str]]:
        """
        Preferred PyWebView GUI backends per platform.

        Returns a list ordered by preference; None indicates auto-detect.
        """
        if self.is_windows:
            return ["edgechromium", None]
        if self.is_macos:
            # PyWebView maps "qt" to PyQtWebEngine when installed
            return ["qt", None]
        # Linux: try Qt first, then GTK, then auto
        return ["qt", "gtk", None]

    def gui_dependency_hint(self) -> str:
        """Human-friendly text describing GUI prerequisites."""
        if self.is_windows:
            return "Install Microsoft Edge WebView2 runtime."
        if self.is_macos:
            return "Install PyQt5 + PyQtWebEngine via pip or Homebrew (pyqt@5)."
        return "Install PyQt5 + PyQtWebEngine (or PyGObject/GTK) via your distro's package manager."


def detect_platform() -> PlatformInfo:
    """Return cached platform information."""
    system = platform.system().lower()
    return PlatformInfo(system=system)


PLATFORM = detect_platform()


"""
CHANGELOG
2025-11-17 Codex
- Added PlatformInfo helper so GUI, CLI, and docs can share cross-platform logic.
"""
