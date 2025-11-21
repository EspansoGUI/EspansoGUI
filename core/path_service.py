from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from core.config_manager import ConfigManager
from core.cli_adapter import CLIAdapter
from core.path_manager import PathManager
from espanso_companion.config_tree import ConfigTreeBuilder
from espanso_companion.yaml_processor import YamlProcessor


class PathService:
    def __init__(
        self,
        loader: PathManager,
        config: ConfigManager,
        cli: CLIAdapter,
        yaml_processor: YamlProcessor,
    ) -> None:
        self.loader = loader
        self.config = config
        self.cli = cli
        self.yaml_processor = yaml_processor
        self._paths = loader.get_paths()
        self._config_override: Optional[Path] = None

    @property
    def paths(self) -> Any:
        return self._paths

    @property
    def config_override(self) -> Optional[Path]:
        return self._config_override

    def initialize(self, override: Optional[Path]) -> None:
        self._config_override = override
        self._paths = self.loader.discover_paths(override)
        self._ensure_directories()
        self.config.ensure_base_yaml(self._paths.match)
        try:
            self.cli.set_config_dir(str(self._paths.config))
        except Exception:
            pass

    def get_path_settings(self) -> Dict[str, Any]:
        env_overrides = {key: str(value) for key, value in self.loader.last_env_paths().items()}
        cli_detected = {key: str(value) for key, value in self.loader.last_cli_paths().items()}
        return {
            "config": str(self._paths.config),
            "match": str(self._paths.match),
            "packages": str(self._paths.packages),
            "runtime": str(self._paths.runtime),
            "override": str(self._config_override or ""),
            "envOverrides": env_overrides,
            "cliDetected": cli_detected,
            "storageRoot": str(self.config.get_data_root()),
            "storageOverride": str(self.config.get_preferences().get("storageRoot") or ""),
            "editorBackups": str(self.config.get_data_root() / "editor_backups"),
            "manualBackups": str(self.config.get_data_root() / "manual_backups"),
            "archiveBackups": str(self.config.get_data_root() / "backups"),
        }

    def set_config_override(self, new_path: str) -> Dict[str, Any]:
        target = self._coerce_override(new_path)
        if target is None or not target.exists() or not target.is_dir():
            return {"status": "error", "detail": f"Config directory not found: {new_path}"}
        self._config_override = target
        self.config.set_preference("configOverride", str(target))
        self.initialize(self._config_override)
        return {"status": "success", "detail": f"Config directory set to {target}", "paths": self.get_path_settings()}

    def clear_config_override(self) -> Dict[str, Any]:
        self._config_override = None
        self.config.set_preference("configOverride", "")
        self.initialize(None)
        return {"status": "success", "detail": "Reverted to auto-detected Espanso paths", "paths": self.get_path_settings()}

    def relocate_config_directory(self, new_path: str, migrate: bool = True) -> Dict[str, Any]:
        target = self._coerce_override(new_path)
        if target is None:
            return {"status": "error", "detail": f"Invalid directory: {new_path}"}
        try:
            target.mkdir(parents=True, exist_ok=True)
            if migrate and self._paths.config.exists():
                self._copy_directory_contents(self._paths.config, target)
        except Exception as exc:
            return {"status": "error", "detail": f"Failed to prepare target directory: {exc}"}
        return self.set_config_override(str(target))

    def set_storage_root(self, new_path: str, migrate: bool = True) -> Dict[str, Any]:
        target = self._coerce_override(new_path)
        if target is None:
            return {"status": "error", "detail": f"Invalid directory: {new_path}"}
        old_root = self.config.get_data_root()
        try:
            target.mkdir(parents=True, exist_ok=True)
            if migrate and old_root.exists() and old_root != target:
                self._copy_directory_contents(old_root, target)
            self.config.set_preference("storageRoot", str(target))
            return {"status": "success", "detail": f"Backups will now use {target}", "paths": self.get_path_settings()}
        except Exception as exc:
            return {"status": "error", "detail": f"Failed to update backup directory: {exc}"}

    def clear_storage_root(self) -> Dict[str, Any]:
        self.config.set_preference("storageRoot", "")
        return {"status": "success", "detail": "Backups now stored in the default profile directory", "paths": self.get_path_settings()}

    def get_config_tree(self) -> Dict[str, Any]:
        builder = ConfigTreeBuilder(self._paths.config, self._paths.match, self.yaml_processor)
        return builder.describe()

    def _ensure_directories(self) -> None:
        for path in (self._paths.config, self._paths.match, self._paths.packages, self._paths.runtime):
            path.mkdir(parents=True, exist_ok=True)

    def _coerce_override(self, raw_value: Optional[str]) -> Optional[Path]:
        if not raw_value:
            return None
        try:
            return Path(raw_value).expanduser()
        except Exception:
            return None

    def _copy_directory_contents(self, source: Path, destination: Path) -> None:
        if not source.exists():
            return
        destination.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            target = destination / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
