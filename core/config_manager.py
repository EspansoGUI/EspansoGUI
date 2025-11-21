from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Manage user preferences and storage directories for Espanso Companion.

    This is a small, testable subset of the functionality previously baked into
    `EspansoAPI`.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        # Allow tests to override where preferences are stored.
        self._base = Path(base_dir) if base_dir is not None else Path.home() / ".espanso_companion"
        self._base.mkdir(parents=True, exist_ok=True)
        self._preferences_path = self._base / "preferences.json"
        self._preferences: Dict[str, Any] = self._load_preferences()

    def _load_preferences(self) -> Dict[str, Any]:
        if not self._preferences_path.exists():
            return {}
        try:
            return json.loads(self._preferences_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_preferences(self) -> None:
        try:
            self._preferences_path.write_text(json.dumps(self._preferences, indent=2), encoding="utf-8")
        except Exception:
            # Best-effort persist; callers can surface errors if required.
            pass

    def get_preferences(self) -> Dict[str, Any]:
        return dict(self._preferences)

    def set_preference(self, key: str, value: Any) -> None:
        self._preferences[key] = value
        self._save_preferences()

    def get_data_root(self) -> Path:
        override = self._preferences.get("storageRoot")
        if override:
            try:
                root = Path(override).expanduser()
                root.mkdir(parents=True, exist_ok=True)
                return root
            except Exception:
                pass
        self._base.mkdir(parents=True, exist_ok=True)
        return self._base

    def ensure_base_yaml(self, match_dir: Path) -> None:
        """Ensure a minimal `base.yml` exists inside the provided match directory."""
        base_file = match_dir / "base.yml"
        if base_file.exists():
            return
        default_content = """# Espanso match file
# Learn more at: https://espanso.org/docs/

matches:
  - trigger: ":hello"
    replace: "Hello from Espanso!"
"""
        try:
            match_dir.mkdir(parents=True, exist_ok=True)
            base_file.write_text(default_content, encoding="utf-8")
        except Exception:
            # Don't raise here; caller may tolerate missing file.
            pass
