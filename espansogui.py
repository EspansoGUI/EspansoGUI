"""PyWebView-based EspansoGUI application."""

from __future__ import annotations

import atexit
import base64
import json
import re
import threading
import uuid
import yaml
from collections import deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import webview

import platform
import shlex
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath, PureWindowsPath

try:
    from snippetsense_engine import SnippetSenseEngine, SnippetSenseUnavailable
except Exception:  # pragma: no cover - optional dependency
    SnippetSenseEngine = None  # type: ignore
    SnippetSenseUnavailable = RuntimeError

from espanso_companion.cli_integration import EspansoCLI
from espanso_companion.config_loader import ConfigLoader
from espanso_companion.config_tree import ConfigTreeBuilder
from espanso_companion.feature_catalog import FeatureCatalog, CatalogSection
from espanso_companion.file_watcher import FileWatcher, WatchEvent
from espanso_companion.variable_engine import VariableEngine
from espanso_companion.yaml_processor import YamlProcessor
from espanso_companion.platform_support import PLATFORM, PlatformInfo



def _section_to_dict(section: CatalogSection) -> Dict[str, Any]:
    return {
        "title": section.title,
        "description": section.description,
        "items": list(section.items),
    }


class EspansoAPI:
    """Exposes the backend surface to the JavaScript dashboard."""

    def __init__(self) -> None:
        self.loader = ConfigLoader()
        self.yaml_processor = YamlProcessor()
        self.variable_engine = VariableEngine()
        self.cli = EspansoCLI()
        self.platform = PLATFORM
        self._events: deque[Dict[str, Any]] = deque(maxlen=60)
        self._event_lock = threading.Lock()
        self._match_cache: List[Dict[str, Any]] = []
        self._yaml_errors: List[Dict[str, Any]] = []
        self._connection_steps: List[Dict[str, Any]] = []
        self._watcher: Optional[FileWatcher] = None
        self._ready = False  # Track initialization completion
        self._preferences = self._load_preferences()
        self._snippetsense_settings = self._preferences.get("snippetsense", self._default_snippetsense_settings())
        self._snippetsense_settings.setdefault("blocked", [])
        self._snippetsense_settings.setdefault("handled", [])
        if "snippetsense" not in self._preferences:
            self._preferences["snippetsense"] = self._snippetsense_settings
            self._save_preferences()
        self._snippetsense_pending = self._load_snippetsense_pending()
        self._snippetsense_engine: Optional[SnippetSenseEngine] = None
        self._snippetsense_engine_error: Optional[str] = None
        self._snippetsense_available = SnippetSenseEngine is not None
        self._snippetsense_app_filters_supported = (
            getattr(SnippetSenseEngine, "APP_DETECTION_SUPPORTED", False) if SnippetSenseEngine else False
        )
        self._snippetsense_lock = threading.Lock()
        self._config_override = self._coerce_override(self._preferences.get("configOverride"))
        self._initialize_paths(self._config_override)
        if self._snippetsense_settings.get("enabled"):
            self._start_snippetsense_engine()
        self._ready = True
        print(f"[INFO] EspansoGUI ready with {len(self._match_cache)} snippets", flush=True)
        atexit.register(self.shutdown)

    def shutdown(self) -> None:
        """Shutdown resources with proper error logging."""
        self._stop_snippetsense_engine()
        watcher = getattr(self, "_watcher", None)
        if not watcher:
            return
        try:
            watcher.stop()
        except Exception as exc:
            # Log the error but don't fail shutdown
            # In production, this could be logged to a file
            print(f"Warning: Error stopping file watcher: {exc}", flush=True)

    def _capture_event(self, event: WatchEvent) -> None:
        """Capture filesystem events with error handling."""
        try:
            entry = {
                "type": event.event_type,
                "file": Path(event.src_path).name if event.src_path else "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            with self._event_lock:
                self._events.appendleft(entry)
        except Exception:
            # Silently ignore errors to prevent watcher thread crash
            # This protects against invalid paths, race conditions, etc.
            pass

    def _initialize_paths(self, override: Optional[Path]) -> None:
        self._paths = self.loader.discover_paths(override)
        print(f"[INFO] Config: {self._paths.config}, Match: {self._paths.match}", flush=True)
        self._ensure_directories()
        self._ensure_base_yaml()
        self._apply_cli_config()
        self._restart_watcher()
        self.refresh_files()

    def _ensure_directories(self) -> None:
        for path in (self._paths.config, self._paths.match, self._paths.packages, self._paths.runtime):
            path.mkdir(parents=True, exist_ok=True)

    def _ensure_base_yaml(self) -> None:
        """Ensure base.yml exists with a minimal default template (never overwrites existing)."""
        base_file = self._paths.match / "base.yml"
        if base_file.exists():
            return

        print(f"[WARNING] base.yml not found, creating default template at {base_file}", flush=True)
        default_content = """# Espanso match file
# Learn more at: https://espanso.org/docs/

matches:
  - trigger: ":hello"
    replace: "Hello from Espanso!"
"""
        try:
            base_file.write_text(default_content, encoding="utf-8")
            print(f"[INFO] Created default base.yml", flush=True)
        except Exception as exc:
            # Log error but don't fail initialization
            print(f"[ERROR] Could not create base.yml: {exc}", flush=True)

    def _start_snippetsense_engine(self) -> None:
        if not self._snippetsense_available or not SnippetSenseEngine:
            self._snippetsense_engine_error = "SnippetSense dependencies missing"
            return
        if self._snippetsense_engine:
            self._snippetsense_engine.update_settings(self._snippetsense_settings)
            return
        try:
            engine = SnippetSenseEngine(self._handle_snippetsense_suggestion)
            engine.start(self._snippetsense_settings)
            self._snippetsense_engine = engine
            self._snippetsense_engine_error = None
        except SnippetSenseUnavailable as exc:
            self._snippetsense_engine_error = str(exc)
            self._snippetsense_engine = None

    def _stop_snippetsense_engine(self) -> None:
        engine = self._snippetsense_engine
        if not engine:
            return
        try:
            engine.stop()
        except Exception:
            pass
        finally:
            self._snippetsense_engine = None

    def _handle_snippetsense_suggestion(self, payload: Dict[str, Any]) -> None:
        suggestion_hash = payload.get("hash")
        if suggestion_hash in (self._snippetsense_settings.get("blocked") or []):
            return
        if suggestion_hash in (self._snippetsense_settings.get("handled") or []):
            return
        suggestion = {
            "id": uuid.uuid4().hex,
            "hash": suggestion_hash,
            "phrase": payload.get("phrase", ""),
            "count": payload.get("count", 0),
            "created": payload.get("timestamp") or datetime.utcnow().isoformat(),
        }
        with self._snippetsense_lock:
            hashes = {item.get("hash") for item in self._snippetsense_pending}
            if suggestion_hash and suggestion_hash in hashes:
                return
            self._snippetsense_pending.append(suggestion)
            if len(self._snippetsense_pending) > 50:
                self._snippetsense_pending = self._snippetsense_pending[-50:]
            self._save_snippetsense_pending()

    def _generate_snippetsense_trigger(self, phrase: str) -> str:
        cleaned = "".join(ch for ch in phrase.lower() if ch.isalnum() or ch.isspace()).strip()
        words = cleaned.split()
        if not words:
            words = ["snippet"]
        base = ":" + "".join(word[:2] for word in words)[:6]
        if len(base) < 3:
            base = ":ss" + cleaned.replace(" ", "")[:3]
        triggers = {snippet.get("trigger") for snippet in (self._match_cache or []) if snippet.get("trigger")}
        candidate = base
        suffix = 1
        while candidate in triggers:
            candidate = f"{base}{suffix}"
            suffix += 1
        return candidate

    def _restart_watcher(self) -> None:
        if self._watcher is not None:
            try:
                self._watcher.stop()
            except Exception:
                pass
        self._watcher = FileWatcher([self._paths.match, self._paths.config])
        self._watcher.register_callback(self._capture_event)
        self._watcher.start()

    def _apply_cli_config(self) -> None:
        try:
            self.cli.set_config_dir(self._paths.config)
        except Exception:
            pass

    @staticmethod
    def _interpret_filter_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "on"}
        if isinstance(value, (int, float)):
            return value != 0
        return False

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        if value in (None, "", False):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sanitize_delay_value(value: Any) -> Optional[int]:
        delay = EspansoAPI._coerce_int(value)
        if delay is None:
            return None
        return delay if delay >= 0 else None

    @staticmethod
    def _normalize_replace_text(text: str, prefer_windows_line_endings: bool = False) -> str:
        if not isinstance(text, str):
            return ""
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        if prefer_windows_line_endings:
            normalized = normalized.replace("\n", "\r\n")
        return normalized

    @staticmethod
    def _parse_offset_expression(expr: str) -> int:
        if not expr:
            return 0
        text = expr.strip().lower()
        pattern = re.compile(r"(?P<sign>[+-]?)(?P<value>\d+)\s*(?P<unit>[a-z]+)")
        match = pattern.fullmatch(text)
        if not match:
            raise ValueError("Use offsets like +7 days or -1 week")
        sign = -1 if match.group("sign") == "-" else 1
        value = int(match.group("value"))
        unit = match.group("unit")
        unit_map = {
            "s": 1,
            "sec": 1,
            "secs": 1,
            "second": 1,
            "seconds": 1,
            "m": 60,
            "min": 60,
            "mins": 60,
            "minute": 60,
            "minutes": 60,
            "h": 3600,
            "hr": 3600,
            "hrs": 3600,
            "hour": 3600,
            "hours": 3600,
            "d": 86400,
            "day": 86400,
            "days": 86400,
            "w": 604800,
            "week": 604800,
            "weeks": 604800,
            "month": 2629746,
            "months": 2629746,
            "y": 31557600,
            "yr": 31557600,
            "yrs": 31557600,
            "year": 31557600,
            "years": 31557600,
        }
        seconds_per_unit = unit_map.get(unit)
        if seconds_per_unit is None:
            raise ValueError(f"Unsupported unit '{unit}'")
        return sign * value * seconds_per_unit

    def _preferences_path(self) -> Path:
        base = Path.home() / ".espanso_companion"
        base.mkdir(parents=True, exist_ok=True)
        return base / "preferences.json"

    def _data_root(self) -> Path:
        override = self._preferences.get("storageRoot") if hasattr(self, "_preferences") else None
        if override:
            try:
                root = Path(str(override)).expanduser()
            except Exception:
                root = Path.home() / ".espanso_companion"
        else:
            root = Path.home() / ".espanso_companion"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _editor_backup_dir(self) -> Path:
        path = self._data_root() / "editor_backups"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _manual_backup_dir(self) -> Path:
        path = self._data_root() / "manual_backups"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _archive_backup_dir(self) -> Path:
        path = self._data_root() / "backups"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _load_preferences(self) -> Dict[str, Any]:
        path = self._preferences_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_preferences(self) -> None:
        path = self._preferences_path()
        path.write_text(json.dumps(self._preferences, indent=2), encoding="utf-8")

    def _default_snippetsense_settings(self) -> Dict[str, Any]:
        return {
            "enabled": False,
            "min_words": 3,
            "min_chars": 10,
            "repetition_threshold": 3,
            "whitelist": [],
            "blacklist": [],
            "blocked": [],
            "handled": [],
        }

    def _snippetsense_state_path(self) -> Path:
        return self._data_root() / "snippetsense_pending.json"

    def _load_snippetsense_pending(self) -> List[Dict[str, Any]]:
        path = self._snippetsense_state_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def _save_snippetsense_pending(self) -> None:
        path = self._snippetsense_state_path()
        try:
            path.write_text(json.dumps(self._snippetsense_pending, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _mark_snippetsense_handled(self, phrase_hash: Optional[str]) -> None:
        if not phrase_hash:
            return
        handled = set(self._snippetsense_settings.get("handled") or [])
        if phrase_hash in handled:
            return
        handled.add(phrase_hash)
        self._snippetsense_settings["handled"] = list(handled)
        self._preferences["snippetsense"] = self._snippetsense_settings
        self._save_preferences()
        if self._snippetsense_engine:
            self._snippetsense_engine.update_settings(self._snippetsense_settings)

    @staticmethod
    def _coerce_override(raw_value: Optional[Any]) -> Optional[Path]:
        if raw_value in (None, ""):
            return None
        try:
            return Path(str(raw_value)).expanduser()
        except Exception:
            return None

    @staticmethod
    def _copy_directory_contents(source: Path, destination: Path) -> None:
        if not source.exists():
            return
        destination.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            target = destination / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

    def _populate_matches(self) -> None:
        """Load and parse all match files with error tracking."""
        matches: List[Dict[str, Any]] = []
        match_dir = self._paths.match

        if not match_dir.exists():
            print(f"[WARNING] Match directory does not exist: {match_dir}", flush=True)
            self._match_cache = matches
            return

        yaml_files = list(match_dir.glob("*.yml"))

        yaml_errors = []
        for file in yaml_files:
            try:
                data = self.yaml_processor.load(file)
            except Exception as exc:
                # Track YAML errors for diagnostics but continue processing
                print(f"[ERROR] Failed to load {file.name}: {exc}", flush=True)
                yaml_errors.append({"file": file.name, "error": str(exc)})
                continue

            try:
                flattened = self.yaml_processor.flatten_matches(data)
                for match in flattened:
                    delay_value = self._sanitize_delay_value(match.delay)
                    has_form = bool(match.form)
                    has_vars = bool(match.variables)
                    matches.append(
                        {
                            "name": match.name,
                            "trigger": match.trigger,
                            "replace": match.replace,
                            "variables": match.variables,
                            "enabled": match.enabled,
                            "file": file.name,
                            "label": match.label or "",
                            "backend": match.backend or "",
                            "delay": delay_value,
                            "left_word": match.left_word,
                            "right_word": match.right_word,
                            "uppercase_style": match.uppercase_style or "",
                            "image_path": match.image_path or "",
                            "word": match.word,
                            "propagate_case": match.propagate_case,
                            "form": match.form,
                            "hasForm": has_form,
                            "hasVars": has_vars,
                        }
                    )
            except Exception as exc:
                # Track processing errors
                print(f"[ERROR] Failed to process matches in {file.name}: {exc}", flush=True)
                yaml_errors.append({"file": file.name, "error": f"Processing error: {exc}"})

        self._match_cache = matches
        print(f"[INFO] Loaded {len(matches)} snippets from {len(yaml_files)} files", flush=True)
        # Store errors for diagnostics (could be exposed to UI later)
        self._yaml_errors = yaml_errors

    def _get_event_snapshot(self) -> List[Dict[str, Any]]:
        with self._event_lock:
            return list(self._events)

    def _run_connection_sequence(self) -> None:
        self._connection_steps = []
        steps: List[Tuple[str, Callable[[], Tuple[str, str]]]] = [
            ("Ensure Espanso CLI", self._ensure_espanso_installed),
            ("Espanso service running", self._start_espanso_service),
            ("Check Espanso version", self._check_cli_available),
            ("Detect configuration paths", self._verify_paths),
            ("Validate YAML structure", self._validate_yaml),
            ("Ensure watcher ping", self._check_watcher),
        ]
        for label, action in steps:
            self._record_step(label, action)

    def _record_step(self, label: str, action: Callable[[], Tuple[str, str]]) -> None:
        try:
            status, detail = action()
        except Exception as exc:
            status = "error"
            detail = str(exc)
        self._connection_steps.append(
            {
                "label": label,
                "status": status,
                "detail": detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def _check_cli_available(self) -> Tuple[str, str]:
        result = self.cli.run(["--version"])
        if result.returncode == 0:
            message = result.stdout.strip() or "Espanso CLI ready"
            return "success", message
        return "error", result.stderr.strip() or result.stdout.strip() or "Espanso CLI missing"

    def _ensure_espanso_installed(self) -> Tuple[str, str]:
        if shutil.which("espanso"):
            return "success", "Espanso CLI already present"
        try:
            installer = self._install_espanso()
            return "success", f"Downloaded installer {installer.name}"
        except Exception as exc:
            return "error", f"Failed to install: {exc}"

    def _install_espanso(self) -> Path:
        """Download and install Espanso with proper error reporting."""
        if platform.system() != "Windows":
            raise RuntimeError("Auto-install supported only on Windows")

        installer_url = "https://github.com/federico-terzi/espanso/releases/latest/download/espanso-setup.exe"
        target = Path(tempfile.gettempdir()) / "espanso-setup.exe"

        try:
            # Download installer with error handling
            urllib.request.urlretrieve(installer_url, target)
        except Exception as exc:
            raise RuntimeError(f"Failed to download Espanso installer: {exc}")

        # Run installer and capture output for diagnostics
        result = subprocess.run(
            [str(target), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
            check=False,  # Don't raise on error - we want to check returncode
            capture_output=True,  # Capture output instead of suppressing
            text=True,
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
            raise RuntimeError(f"Espanso installer failed: {error_msg}")

        return target

    def _start_espanso_service(self) -> Tuple[str, str]:
        """Ensure the Espanso daemon is running without spamming start commands."""
        status_result = self.cli.run(["status"])
        status_output = (status_result.stdout or status_result.stderr or "").strip()
        if status_result.returncode == 0 and "running" in status_output.lower():
            return "success", status_output or "Espanso already running"

        result = self.cli.run(["start"])
        if result.returncode == 0:
            return "success", "Espanso daemon started"
        detail = result.stdout.strip() or result.stderr.strip()
        state = detail.lower()
        if "already running" in state:
            return "success", detail or "Espanso already running"
        return "error", detail or "start command failed"

    def _verify_paths(self) -> Tuple[str, str]:
        details = ", ".join(
            f"{name}: {path}"
            for name, path in self._paths.__dict__.items()
        )
        return "success", details

    def _validate_yaml(self) -> Tuple[str, str]:
        match_files = list(self._paths.match.glob("*.yml"))
        if not match_files:
            return "warning", "No match files yet; waiting for snippets."
        try:
            self.yaml_processor.load(match_files[0])
            return "success", f"Parsed {match_files[0].name}"
        except Exception as exc:
            return "error", f"YAML parse failed: {exc}"

    def _check_watcher(self) -> Tuple[str, str]:
        observer = getattr(self._watcher, "_observer", None)
        if observer is not None and observer.is_alive():
            return "success", "Filesystem watcher active"
        return "warning", "Watcher not running yet"

    def _autostart_status(self) -> Dict[str, str]:
        """Check if espanso is registered as a system service (autostart)."""
        # In Espanso 2.x, the command is 'service check' not 'autostart status'
        result = self.cli.run(["service", "check"])
        detail = result.stdout.strip() or result.stderr.strip()

        # Exit code 2 means "not registered" which is a valid state
        if result.returncode == 0:
            # Successfully registered
            return {"status": "success", "detail": detail or "Auto-start enabled"}
        elif result.returncode == 2:
            # Not registered (expected when autostart is disabled)
            return {"status": "warning", "detail": detail or "Auto-start disabled"}
        else:
            # Other error
            return {"status": "error", "detail": detail or "Unable to check autostart status"}

    def _run_package_command(self, args: List[str]) -> Dict[str, str]:
        result = self.cli.run(args)
        detail = result.stdout.strip() or result.stderr.strip()
        status = "success" if result.returncode == 0 else "error"
        return {"status": status, "detail": detail or f"Command {' '.join(args)} completed"}

    def get_dashboard(self) -> Dict[str, Any]:
        """Get dashboard data with defensive initialization."""
        # Only repopulate if cache is empty (don't reload on every call)
        if not self._match_cache:
            self._populate_matches()

        status = self.cli.status()
        self._run_connection_sequence()

        # Use cached data with fallbacks
        matches = self._match_cache if self._match_cache else []
        form_snippets = sum(1 for snippet in matches if snippet.get("hasForm", False))
        var_snippets = sum(1 for snippet in matches if snippet.get("hasVars", False))
        recent_events = self._get_event_snapshot()

        # Count match files safely
        match_files = 0
        if self._paths and self._paths.match and self._paths.match.exists():
            match_files = len(list(self._paths.match.glob("*.yml")))

        return {
            "configPath": str(self._paths.config) if self._paths else "Not configured",
            "statusMessage": "Connected" if status["returncode"] == 0 else "CLI unavailable",
            "cliStatus": status["stdout"] or status["stderr"] or "Ready",
            "snippetCount": len(matches),
            "matchFileCount": match_files,
            "formSnippets": form_snippets,
            "variableSnippets": var_snippets,
            "eventCount": len(recent_events),
            "recentEvents": recent_events[:10] if recent_events else [],
            "connectionSteps": self._connection_steps if self._connection_steps else [],
        }

    def ping(self) -> Dict[str, Any]:
        """Lightweight readiness probe for the frontend bootstrap loop."""
        return {
            "status": "ok",
            "ready": self._ready,
            "snippetCount": len(self._match_cache or []),
            "configPath": str(self._paths.config) if self._paths else "",
            "platform": self.platform.system,
        }

    def get_settings(self) -> Dict[str, Any]:
        status = self.cli.status()
        autostart = self._autostart_status()
        return {
            "serviceStatus": status["stdout"].strip() or status["stderr"].strip() or "Unknown",
            "autostart": autostart,
            "packages": self.cli.packages(),
        }

    def get_path_settings(self) -> Dict[str, Any]:
        env_overrides = {key: str(value) for key, value in self.loader.last_env_paths().items()}
        cli_detected = {key: str(value) for key, value in self.loader.last_cli_paths().items()}
        editor_backup = self._editor_backup_dir()
        manual_backup = self._manual_backup_dir()
        archive_backup = self._archive_backup_dir()
        return {
            "config": str(self._paths.config),
            "match": str(self._paths.match),
            "packages": str(self._paths.packages),
            "runtime": str(self._paths.runtime),
            "override": str(self._config_override) if self._config_override else "",
            "envOverrides": env_overrides,
            "cliDetected": cli_detected,
            "storageRoot": str(self._data_root()),
            "storageOverride": str(self._preferences.get("storageRoot") or ""),
            "editorBackups": str(editor_backup),
            "manualBackups": str(manual_backup),
            "archiveBackups": str(archive_backup),
        }

    def set_config_override(self, new_path: str) -> Dict[str, Any]:
        target = self._coerce_override(new_path)
        if target is None or not target.exists() or not target.is_dir():
            return {"status": "error", "detail": f"Config directory not found: {new_path}"}
        self._config_override = target
        self._preferences["configOverride"] = str(target)
        self._save_preferences()
        self._initialize_paths(self._config_override)
        return {"status": "success", "detail": f"Config directory set to {target}", "paths": self.get_path_settings()}

    def relocate_config_directory(self, new_path: str, migrate: bool = True) -> Dict[str, Any]:
        target = self._coerce_override(new_path)
        if target is None:
            return {"status": "error", "detail": f"Invalid directory: {new_path}"}
        try:
            target.mkdir(parents=True, exist_ok=True)
            if migrate and self._paths and self._paths.config.exists():
                self._copy_directory_contents(self._paths.config, target)
        except Exception as exc:
            return {"status": "error", "detail": f"Failed to prepare target directory: {exc}"}
        return self.set_config_override(str(target))

    def clear_config_override(self) -> Dict[str, Any]:
        self._config_override = None
        if "configOverride" in self._preferences:
            self._preferences.pop("configOverride")
            self._save_preferences()
        self._initialize_paths(self._config_override)
        return {"status": "success", "detail": "Reverted to auto-detected Espanso paths", "paths": self.get_path_settings()}

    def set_storage_root(self, new_path: str, migrate: bool = True) -> Dict[str, Any]:
        target = self._coerce_override(new_path)
        if target is None:
            return {"status": "error", "detail": f"Invalid directory: {new_path}"}
        old_root = self._data_root()
        try:
            target.mkdir(parents=True, exist_ok=True)
            if migrate and old_root.exists() and old_root != target:
                self._copy_directory_contents(old_root, target)
            self._preferences["storageRoot"] = str(target)
            self._save_preferences()
            return {"status": "success", "detail": f"Backups will now use {target}", "paths": self.get_path_settings()}
        except Exception as exc:
            return {"status": "error", "detail": f"Failed to update backup directory: {exc}"}

    def clear_storage_root(self) -> Dict[str, Any]:
        if "storageRoot" in self._preferences:
            self._preferences.pop("storageRoot")
            self._save_preferences()
        return {"status": "success", "detail": "Backups now stored in the default profile directory", "paths": self.get_path_settings()}

    def get_config_tree(self) -> Dict[str, Any]:
        builder = ConfigTreeBuilder(self._paths.config, self._paths.match, self.yaml_processor)
        return builder.describe()

    def pick_path_dialog(self, prompt: str = "Select a file", directory: bool = False) -> Dict[str, Any]:
        """Expose a pywebview file/folder picker to the frontend."""
        try:
            window = webview.windows[0]
        except IndexError:
            return {"status": "error", "detail": "No active window"}

        dialog_type = webview.FOLDER_DIALOG if directory else webview.OPEN_DIALOG
        try:
            result = window.create_file_dialog(dialog_type, directory=str(self._paths.config), allow_multiple=False)
        except Exception as exc:
            return {"status": "error", "detail": f"Picker failed: {exc}"}

        if not result:
            return {"status": "cancelled"}

        path = result if directory else result[0]
        return {"status": "success", "path": path}

    def get_image_preview(self, path: str) -> Dict[str, Any]:
        """Return a small base64 preview for an image path."""
        try:
            if not path:
                return {"status": "error", "detail": "Path is required"}
            file_path = Path(path).expanduser()
            if not file_path.exists() or not file_path.is_file():
                return {"status": "error", "detail": f"Image not found: {file_path}"}
            max_bytes = 2 * 1024 * 1024
            if file_path.stat().st_size > max_bytes:
                return {"status": "error", "detail": "Image is larger than 2MB"}
            suffix = file_path.suffix.lower().lstrip(".")
            mime_map = {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "gif": "image/gif",
                "bmp": "image/bmp",
                "webp": "image/webp",
            }
            mime = mime_map.get(suffix, "image/png")
            encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
            return {"status": "success", "data": f"data:{mime};base64,{encoded}"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def toggle_autostart(self, enable: bool) -> Dict[str, str]:
        """Enable or disable espanso autostart (system service registration)."""
        # In Espanso 2.x, the commands are 'service register' / 'service unregister'
        cmd = "register" if enable else "unregister"
        result = self.cli.run(["service", cmd])
        detail = result.stdout.strip() or result.stderr.strip()
        status = "success" if result.returncode == 0 else "error"
        return {"status": status, "detail": detail or f"Autostart {cmd} completed"}

    def install_package(self, name: str) -> Dict[str, str]:
        return self._run_package_command(["package", "install", name])

    def start_service(self) -> Dict[str, str]:
        result = self.cli.run(["start"])
        detail = result.stdout.strip() or result.stderr.strip()
        status = "success" if result.returncode == 0 else "warning"
        return {"status": status, "detail": detail or "Espanso start requested"}

    def stop_service(self) -> Dict[str, str]:
        result = self.cli.run(["stop"])
        detail = result.stdout.strip() or result.stderr.strip()
        status = "success" if result.returncode == 0 else "warning"
        return {"status": status, "detail": detail or "Espanso stop requested"}

    def restart_service(self) -> Dict[str, str]:
        result = self.cli.reload()
        detail = result.stdout.strip() or result.stderr.strip()
        status = "success" if result.returncode == 0 else "warning"
        return {"status": status, "detail": detail or "Espanso restart issued"}

    def test_shell_command(self, command: str, timeout: int = 5, use_shell: bool = True) -> Dict[str, Any]:
        """Execute a shell command for the shell variable helper."""
        if not command:
            return {"status": "error", "detail": "Command is required"}
        try:
            completed = subprocess.run(
                command if use_shell else shlex.split(command),
                capture_output=True,
                text=True,
                timeout=max(1, min(timeout, 30)),
                shell=use_shell,
                cwd=str(self._paths.config),
            )
            output = (completed.stdout or completed.stderr or "").strip()
            status = "success" if completed.returncode == 0 else "error"
            detail = output or f"Exit code {completed.returncode}"
            return {"status": status, "output": output, "detail": detail}
        except subprocess.TimeoutExpired:
            return {"status": "error", "detail": "Command timed out"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def get_logs(self, lines: int = 100) -> Dict[str, Any]:
        """Get recent Espanso logs."""
        try:
            result = self.cli.run(["log"])
            logs = result.stdout.strip().split('\n')[-lines:]
            return {"status": "success", "logs": logs}
        except Exception as e:
            return {"status": "error", "logs": [], "detail": str(e)}

    def list_packages(self) -> Dict[str, Any]:
        """List installed packages."""
        try:
            result = self.cli.run(["package", "list"])
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                return {"status": "success", "packages": lines}
            return {"status": "error", "packages": [], "detail": result.stderr}
        except Exception as e:
            return {"status": "error", "packages": [], "detail": str(e)}

    def package_operation(self, operation: str, package_name: str = "") -> Dict[str, str]:
        """Execute package operation: install, uninstall, update."""
        try:
            cmd = ["package", operation]
            if package_name:
                cmd.append(package_name)
            result = self.cli.run(cmd)
            status = "success" if result.returncode == 0 else "error"
            detail = result.stdout.strip() or result.stderr.strip()
            return {"status": status, "detail": detail}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def create_app_config(self, app_name: str, filter_exec: str = "", filter_title: str = "") -> Dict[str, str]:
        """Create app-specific config file."""
        try:
            config_dir = self._paths.config / "config"
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / f"{app_name}.yml"
            if config_file.exists():
                return {"status": "error", "detail": f"{app_name}.yml already exists"}

            content = f"# App-specific config for {app_name}\n\n"
            if filter_exec or filter_title:
                content += "filter_exec: " + (f'"{filter_exec}"' if filter_exec else '""') + "\n"
                if filter_title:
                    content += f'filter_title: "{filter_title}"\n'
                content += "\nmatches:\n  - trigger: \":example\"\n    replace: \"App-specific snippet\"\n"

            config_file.write_text(content, encoding="utf-8")
            return {"status": "success", "detail": f"Created {app_name}.yml"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def list_app_configs(self) -> Dict[str, Any]:
        """List all app-specific config files."""
        try:
            config_dir = self._paths.config / "config"
            if not config_dir.exists():
                return {"status": "success", "configs": []}

            configs = []
            for yml_file in config_dir.glob("*.yml"):
                if yml_file.name == "default.yml":
                    continue
                try:
                    content = yml_file.read_text(encoding="utf-8")
                    filter_exec = ""
                    filter_title = ""
                    for line in content.split('\n'):
                        if line.strip().startswith('filter_exec:'):
                            filter_exec = line.split(':', 1)[1].strip().strip('"')
                        elif line.strip().startswith('filter_title:'):
                            filter_title = line.split(':', 1)[1].strip().strip('"')
                    configs.append({
                        "name": yml_file.stem,
                        "filter_exec": filter_exec,
                        "filter_title": filter_title,
                        "path": str(yml_file)
                    })
                except Exception:
                    continue
            return {"status": "success", "configs": configs}
        except Exception as e:
            return {"status": "error", "configs": [], "detail": str(e)}

    def test_match(self, text: str) -> Dict[str, Any]:
        """Test if text would trigger a match."""
        try:
            result = self.cli.run(["match", "exec", text])
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            matched = result.returncode == 0 and bool(stdout)
            if matched:
                return {
                    "status": "success",
                    "matched": True,
                    "output": stdout,
                    "input": text,
                }
            detail = stderr or stdout or "No match output returned"
            status = "not_found" if result.returncode == 0 else "error"
            return {
                "status": status,
                "matched": False,
                "detail": detail,
                "input": text,
                "stdout": stdout,
                "stderr": stderr,
            }
        except Exception as e:
            return {"status": "error", "matched": False, "detail": str(e)}

    def backup_config(self) -> Dict[str, str]:
        """Create manual backup of entire config directory."""
        try:
            import shutil
            from datetime import datetime

            backup_dir = self._manual_backup_dir()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"config_backup_{timestamp}"
            backup_path = backup_dir / backup_name

            config_dir = self._paths.config
            shutil.copytree(config_dir, backup_path)

            return {"status": "success", "detail": f"Backup created: {backup_name}", "path": str(backup_path)}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def restore_config(self, backup_name: str) -> Dict[str, str]:
        """Restore config from backup."""
        try:
            import shutil

            backup_dir = self._manual_backup_dir()
            backup_path = backup_dir / backup_name

            if not backup_path.exists():
                return {"status": "error", "detail": f"Backup not found: {backup_name}"}

            config_dir = self._paths.config
            temp_backup = config_dir.parent / f"{config_dir.name}_temp_backup"

            if config_dir.exists():
                shutil.move(str(config_dir), str(temp_backup))

            try:
                shutil.copytree(backup_path, config_dir)
                if temp_backup.exists():
                    shutil.rmtree(temp_backup)
                self._match_cache = []
                self._populate_matches()
                return {"status": "success", "detail": f"Restored from: {backup_name}"}
            except Exception as e:
                if temp_backup.exists():
                    if config_dir.exists():
                        shutil.rmtree(config_dir)
                    shutil.move(str(temp_backup), str(config_dir))
                raise e
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def list_backups(self) -> Dict[str, Any]:
        """List available manual backups."""
        try:
            backup_dir = self._manual_backup_dir()
            if not backup_dir.exists():
                return {"status": "success", "backups": []}

            backups = []
            for item in sorted(backup_dir.iterdir(), reverse=True):
                if item.is_dir():
                    backups.append({
                        "name": item.name,
                        "path": str(item),
                        "created": item.stat().st_mtime
                    })
            return {"status": "success", "backups": backups}
        except Exception as e:
            return {"status": "error", "backups": [], "detail": str(e)}

    def get_snippetsense_state(self) -> Dict[str, Any]:
        status = {
            "available": self._snippetsense_available,
            "running": bool(self._snippetsense_engine),
            "error": self._snippetsense_engine_error,
            "pending": len(self._snippetsense_pending),
            "platform": platform.system().lower(),
            "appFiltersSupported": self._snippetsense_app_filters_supported,
        }
        return {
            "status": status,
            "settings": self._snippetsense_settings,
            "pending": self._snippetsense_pending,
        }

    def save_snippetsense_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        try:
            sanitized = self._default_snippetsense_settings()
            sanitized.update({
                "enabled": bool(settings.get("enabled")),
                "min_words": max(1, int(settings.get("min_words", 3))),
                "min_chars": max(5, int(settings.get("min_chars", 10))),
                "repetition_threshold": max(2, int(settings.get("repetition_threshold", 3))),
                "whitelist": settings.get("whitelist") or [],
                "blacklist": settings.get("blacklist") or [],
                "blocked": self._snippetsense_settings.get("blocked") or [],
                "handled": self._snippetsense_settings.get("handled") or [],
            })
            self._snippetsense_settings = sanitized
            self._preferences["snippetsense"] = sanitized
            self._save_preferences()
            if sanitized["enabled"]:
                self._start_snippetsense_engine()
            else:
                self._stop_snippetsense_engine()
            return {"status": "success", "detail": "SnippetSense settings updated", "settings": sanitized}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def list_snippetsense_suggestions(self) -> Dict[str, Any]:
        with self._snippetsense_lock:
            pending = list(self._snippetsense_pending)
        return {"status": "success", "pending": pending}

    def handle_snippetsense_decision(self, suggestion_id: str, decision: str) -> Dict[str, Any]:
        decision = (decision or "").lower()
        if decision not in {"accept", "reject", "never"}:
            return {"status": "error", "detail": f"Unsupported decision: {decision}"}
        suggestion = None
        with self._snippetsense_lock:
            for item in self._snippetsense_pending:
                if item.get("id") == suggestion_id:
                    suggestion = item
                    break
            if not suggestion:
                return {"status": "error", "detail": "Suggestion not found"}
            self._snippetsense_pending = [item for item in self._snippetsense_pending if item.get("id") != suggestion_id]
            self._save_snippetsense_pending()

        phrase_hash = suggestion.get("hash")
        if decision == "accept":
            phrase = suggestion.get("phrase") or ""
            trigger = self._generate_snippetsense_trigger(phrase)
            payload = {
                "trigger": trigger,
                "replace": phrase,
                "label": "SnippetSense",
                "enabled": True,
            }
            result = self.create_snippet(payload)
            snippet_payload = None
            snippet_data = self.get_snippet(trigger)
            if snippet_data.get("status") == "success":
                snippet_payload = snippet_data.get("snippet")
            self._mark_snippetsense_handled(phrase_hash)
            blocked = set(self._snippetsense_settings.get("blocked") or [])
            if phrase_hash:
                blocked.add(phrase_hash)
                self._snippetsense_settings["blocked"] = list(blocked)
                self._preferences["snippetsense"] = self._snippetsense_settings
                self._save_preferences()
            return {
                "status": result.get("status", "success"),
                "detail": result.get("detail", "Snippet created"),
                "trigger": trigger,
                "snippet": snippet_payload,
            }

        if decision == "never":
            phrase_hash = suggestion.get("hash")
            blocked = set(self._snippetsense_settings.get("blocked") or [])
            if phrase_hash:
                blocked.add(phrase_hash)
            self._snippetsense_settings["blocked"] = list(blocked)
            self._preferences["snippetsense"] = self._snippetsense_settings
            self._save_preferences()
            if self._snippetsense_engine:
                self._snippetsense_engine.update_settings(self._snippetsense_settings)
            self._mark_snippetsense_handled(phrase_hash)
            return {"status": "success", "detail": "Phrase will no longer trigger suggestions"}

        self._mark_snippetsense_handled(phrase_hash)
        return {"status": "success", "detail": "Suggestion dismissed"}

    def doctor_diagnostics(self) -> Dict[str, Any]:
        """Run espanso doctor to get diagnostics."""
        try:
            result = self.cli.run(["doctor"])
            output = result.stdout.strip() if result.stdout else result.stderr.strip()
            return {"status": "success", "output": output, "exit_code": result.returncode}
        except Exception as e:
            return {"status": "error", "output": str(e), "exit_code": -1}

    def uninstall_package(self, package_name: str) -> Dict[str, str]:
        """Uninstall a package."""
        try:
            result = self.cli.run(["package", "uninstall", package_name])
            status = "success" if result.returncode == 0 else "error"
            detail = result.stdout.strip() or result.stderr.strip()
            return {"status": status, "detail": detail or f"Uninstalled {package_name}"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def get_app_config_templates(self) -> Dict[str, Any]:
        """Get preset app-specific config templates."""
        templates = {
            "vscode": {
                "filter_exec": "code.exe",
                "filter_title": "",
                "snippets": [
                    {"trigger": ":log", "replace": "console.log($|$);"},
                    {"trigger": ":func", "replace": "function $|$() {\n  \n}"},
                ]
            },
            "chrome": {
                "filter_exec": "chrome.exe",
                "filter_title": "",
                "snippets": [
                    {"trigger": ":email", "replace": "your.email@example.com"},
                ]
            },
            "slack": {
                "filter_exec": "slack.exe",
                "filter_title": "",
                "snippets": [
                    {"trigger": ":shrug", "replace": "¯\\_(ツ)_/¯"},
                    {"trigger": ":thanks", "replace": "Thanks for letting me know!"},
                ]
            },
            "terminal": {
                "filter_exec": "WindowsTerminal.exe",
                "filter_title": "",
                "snippets": [
                    {"trigger": ":gst", "replace": "git status"},
                    {"trigger": ":gco", "replace": "git checkout $|$"},
                ]
            },
            "outlook": {
                "filter_exec": "outlook.exe",
                "filter_title": "",
                "snippets": [
                    {"trigger": ":sig", "replace": "Best regards,\nYour Name\nYour Title"},
                ]
            }
        }
        return {"status": "success", "templates": templates}

    def import_snippet_pack(self, file_path: str) -> Dict[str, str]:
        """Import snippets from JSON/YAML file."""
        try:
            import json
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {"status": "error", "detail": "File not found"}

            content = file_path_obj.read_text(encoding="utf-8")
            if file_path.endswith('.json'):
                snippets = json.loads(content)
            else:
                snippets = yaml.safe_load(content)

            if not isinstance(snippets, list):
                snippets = snippets.get('matches', [])

            count = 0
            for snippet in snippets:
                if 'trigger' in snippet and 'replace' in snippet:
                    self.create_snippet(snippet)
                    count += 1

            return {"status": "success", "detail": f"Imported {count} snippets"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def export_snippet_pack(self, triggers: list, file_path: str) -> Dict[str, str]:
        """Export selected snippets to JSON file."""
        try:
            import json
            snippets = []
            for trigger in triggers:
                snippet = self.get_snippet(trigger)
                if snippet.get('status') == 'success':
                    snippets.append(snippet.get('snippet', {}))

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(snippets, f, indent=2, ensure_ascii=False)

            return {"status": "success", "detail": f"Exported {len(snippets)} snippets"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def get_global_variables(self) -> Dict[str, Any]:
        """Get all global variables from base config."""
        try:
            base_file = self._paths.match / "base.yml"
            if not base_file.exists():
                return {"status": "success", "variables": []}

            with open(base_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}

            normalized: List[Dict[str, Any]] = []
            for raw in data.get('global_vars', []) or []:
                item = dict(raw or {})
                var_type = item.get('type') or item.get('var_type') or ''
                name = item.get('name', '')
                params = item.get('params') or {}
                normalized.append({
                    "name": name,
                    "type": var_type,
                    "params": params,
                })
            return {"status": "success", "variables": normalized}
        except Exception as e:
            return {"status": "error", "variables": [], "detail": str(e)}

    def update_global_variables(self, variables: list) -> Dict[str, str]:
        """Update global variables in base config."""
        try:
            base_file = self._paths.match / "base.yml"
            if not base_file.exists():
                return {"status": "error", "detail": "base.yml not found"}

            with open(base_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}

            sanitized: List[Dict[str, Any]] = []
            for item in variables or []:
                name = (item.get('name') or '').strip()
                var_type = (item.get('type') or item.get('var_type') or '').strip()
                if not name or not var_type:
                    continue
                entry: Dict[str, Any] = {"name": name, "type": var_type}
                params = item.get('params') or {}
                if params:
                    entry['params'] = params
                sanitized.append(entry)

            data['global_vars'] = sanitized

            with open(base_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            return {"status": "success", "detail": "Global variables updated"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def validate_regex(self, pattern: str) -> Dict[str, Any]:
        """Validate a regex pattern."""
        try:
            import re
            re.compile(pattern)
            return {"status": "success", "valid": True, "detail": "Valid regex pattern"}
        except re.error as e:
            return {"status": "success", "valid": False, "detail": str(e)}
        except Exception as e:
            return {"status": "error", "valid": False, "detail": str(e)}

    def test_regex(self, pattern: str, test_text: str) -> Dict[str, Any]:
        """Test regex pattern against text."""
        try:
            import re
            compiled = re.compile(pattern)
            match = compiled.search(test_text)
            if match:
                return {
                    "status": "success",
                    "matched": True,
                    "match_text": match.group(0),
                    "groups": list(match.groups()),
                    "span": match.span()
                }
            else:
                return {"status": "success", "matched": False}
        except re.error as e:
            return {"status": "error", "matched": False, "detail": f"Regex error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "matched": False, "detail": str(e)}

    def preview_date_offset(self, fmt: str, expression: str) -> Dict[str, Any]:
        """Preview a formatted date with the provided offset expression."""
        try:
            seconds = self._parse_offset_expression(expression)
            target = datetime.now() + timedelta(seconds=seconds)
            preview = target.strftime(fmt or "%Y-%m-%d")
            return {"status": "success", "preview": preview, "seconds": seconds}
        except ValueError as exc:
            return {"status": "error", "detail": str(exc)}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def create_form_snippet(self, trigger: str, form_fields: list) -> Dict[str, str]:
        """Create a snippet with form fields."""
        try:
            if not trigger:
                return {"status": "error", "detail": "Trigger is required"}

            replacement_parts = []
            form_def = []

            for i, field in enumerate(form_fields):
                field_name = field.get('name', f'field{i}') or f'field{i}'
                field_type = field.get('type', 'text')
                normalized_type = field_type
                if field_type == 'radio':
                    normalized_type = 'choice'
                elif field_type == 'select':
                    normalized_type = 'list'

                field_obj = {'name': field_name, 'type': normalized_type}
                values = [str(v) for v in field.get('values') or [] if str(v).strip()]
                if normalized_type in {'choice', 'list'}:
                    if not values:
                        return {"status": "error", "detail": f"{field_name} requires at least one option"}
                    field_obj['values'] = values
                if normalized_type == 'checkbox':
                    field_obj['default'] = bool(field.get('default'))
                elif normalized_type == 'text' and field.get('default'):
                    field_obj['default'] = field['default']

                form_def.append(field_obj)
                replacement_parts.append(f"{{{{{field_name}}}}}")

            replacement = " ".join(replacement_parts)

            snippet = {
                'trigger': trigger,
                'form': form_def,
                'replace': replacement
            }

            return self.create_snippet(snippet)
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def list_snippets(self) -> List[Dict[str, Any]]:
        """Return cached snippets, populating if necessary."""
        if not self._match_cache:
            self._populate_matches()
        return self._match_cache if self._match_cache else []

    def _snippet_matches_filters(self, snippet: Dict[str, Any], query: str, filters: Dict[str, Any]) -> bool:
        file_filter = (filters.get("file") or "").strip().lower()
        if file_filter and (snippet.get("file") or "").lower() != file_filter:
            return False

        enabled_filter = (filters.get("enabled") or "").strip().lower()
        enabled_value = snippet.get("enabled", True)
        if enabled_filter == "enabled" and enabled_value is False:
            return False
        if enabled_filter == "disabled" and not (enabled_value is False):
            return False

        if self._interpret_filter_bool(filters.get("hasVars")) and not snippet.get("hasVars"):
            return False
        if self._interpret_filter_bool(filters.get("hasForm")) and not snippet.get("hasForm"):
            return False

        label_filter = (filters.get("label") or "").strip().lower()
        if label_filter and label_filter not in (snippet.get("label") or "").lower():
            return False

        if query:
            haystack_parts = [
                snippet.get("trigger") or "",
                snippet.get("replace") or "",
                snippet.get("label") or "",
                snippet.get("file") or "",
            ]
            haystack = " ".join(haystack_parts).lower()
            if query not in haystack:
                return False

        return True

    def search_snippets(self, query: str = "", filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Search snippets with optional filters."""
        try:
            if not self._match_cache:
                self._populate_matches()
            snippets = self._match_cache if self._match_cache else []
            normalized_query = (query or "").strip().lower()
            filters = filters or {}
            results = [
                snippet
                for snippet in snippets
                if self._snippet_matches_filters(snippet, normalized_query, filters)
            ]
            return {
                "status": "success",
                "results": results,
                "count": len(results),
                "total": len(snippets),
            }
        except Exception as exc:
            return {"status": "error", "detail": f"Failed to search snippets: {exc}"}

    def refresh_files(self) -> Dict[str, Any]:
        self._populate_matches()
        return self.get_dashboard()

    def get_base_yaml(self) -> Dict[str, Any]:
        """Read the base.yaml file for editing."""
        base_file = self._paths.match / "base.yml"
        try:
            if base_file.exists():
                content = base_file.read_text(encoding="utf-8")
                return {"status": "success", "content": content, "path": str(base_file)}
            else:
                return {"status": "error", "content": "", "detail": "base.yml not found"}
        except Exception as exc:
            return {"status": "error", "content": "", "detail": f"Failed to read base.yml: {exc}"}

    def save_base_yaml(self, content: str) -> Dict[str, str]:
        """Save the base.yaml file after editing."""
        base_file = self._paths.match / "base.yml"
        try:
            # Validate YAML syntax before saving
            self.yaml_processor.load_str(content)

            # Create backup before saving
            if base_file.exists():
                backup_dir = self._editor_backup_dir()
                backup_file = backup_dir / f"base.yml.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.bak"
                backup_file.write_text(base_file.read_text(encoding="utf-8"), encoding="utf-8")

            # Save new content
            base_file.write_text(content, encoding="utf-8")

            # Refresh snippets cache
            self.refresh_files()

            # Reload espanso to apply changes
            self.cli.run(["restart"])

            return {"status": "success", "detail": f"Saved and reloaded Espanso"}
        except Exception as exc:
            return {"status": "error", "detail": f"Failed to save: {exc}"}

    # ========================================
    # SNIPPET CRUD OPERATIONS
    # ========================================

    def _assign_snippet_optional_fields(self, match: Dict[str, Any], snippet_data: Dict[str, Any]) -> None:
        """Apply optional snippet properties while keeping Espanso schema intact."""
        bool_fields = ["word", "propagate_case", "left_word", "right_word"]
        for field in bool_fields:
            if snippet_data.get(field):
                match[field] = True
            else:
                match.pop(field, None)

        if snippet_data.get("vars"):
            match["vars"] = snippet_data["vars"]
        else:
            match.pop("vars", None)

        if snippet_data.get("form"):
            match["form"] = snippet_data["form"]
        else:
            match.pop("form", None)

        label = (snippet_data.get("label") or "").strip()
        if label:
            match["label"] = label
        else:
            match.pop("label", None)

        backend = (snippet_data.get("backend") or "").strip().lower()
        if backend in ["inject", "clipboard"]:
            match["backend"] = backend.capitalize()
        else:
            match.pop("backend", None)

        delay_value = self._sanitize_delay_value(snippet_data.get("delay"))
        if delay_value is not None:
            match["delay"] = delay_value
        else:
            match.pop("delay", None)

        uppercase_style = (snippet_data.get("uppercase_style") or "").strip()
        if uppercase_style:
            match["uppercase_style"] = uppercase_style
        else:
            match.pop("uppercase_style", None)

        image_path = (snippet_data.get("image_path") or "").strip()
        if image_path:
            match["image_path"] = image_path
        else:
            match.pop("image_path", None)

        enabled = snippet_data.get("enabled")
        if enabled is False:
            match["enabled"] = False
        else:
            match.pop("enabled", None)

    def create_snippet(self, snippet_data: Dict[str, Any]) -> Dict[str, str]:
        """Create a new snippet in base.yml."""
        try:
            trigger = (snippet_data.get("trigger") or "").strip()
            replace = self._normalize_replace_text(
                snippet_data.get("replace", ""),
                prefer_windows_line_endings=self.platform.is_windows,
            )
            if not trigger or not replace.strip():
                return {"status": "error", "detail": "Trigger and replacement are required"}

            base_file = self._paths.match / "base.yml"

            # Load existing content
            if base_file.exists():
                data = self.yaml_processor.load(base_file)
            else:
                data = {"matches": []}

            # Ensure match list exists
            matches = data.setdefault("matches", [])
            if any(match.get("trigger") == trigger for match in matches):
                return {"status": "error", "detail": f"Snippet '{trigger}' already exists"}

            # Build new match object
            new_match = {"trigger": trigger, "replace": replace}
            self._assign_snippet_optional_fields(new_match, snippet_data)

            matches.append(new_match)

            # Save back to file
            backup_dir = self._editor_backup_dir()
            backup_file = backup_dir / f"base.yml.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.bak"
            if base_file.exists():
                backup_file.write_text(base_file.read_text(encoding="utf-8"), encoding="utf-8")

            import yaml

            base_file.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            # Refresh and reload
            self.refresh_files()
            self.cli.run(["restart"])

            return {"status": "success", "detail": f"Created snippet '{trigger}'"}
        except Exception as exc:
            return {"status": "error", "detail": f"Failed to create snippet: {exc}"}

    def update_snippet(self, original_trigger: str, snippet_data: Dict[str, Any]) -> Dict[str, str]:
        """Update an existing snippet in base.yml."""
        try:
            base_file = self._paths.match / "base.yml"

            if not base_file.exists():
                return {"status": "error", "detail": "base.yml not found"}

            data = self.yaml_processor.load(base_file)

            trigger = (snippet_data.get("trigger") or "").strip()
            replace = self._normalize_replace_text(
                snippet_data.get("replace", ""),
                prefer_windows_line_endings=self.platform.is_windows,
            )
            if not trigger or not replace.strip():
                return {"status": "error", "detail": "Trigger and replacement are required"}

            # Find the match to update
            found = False
            for match in data.get("matches", []):
                if match.get("trigger") == original_trigger:
                    # Update fields
                    match["trigger"] = trigger
                    match["replace"] = replace

                    # Update optional properties
                    self._assign_snippet_optional_fields(match, snippet_data)

                    found = True
                    break

            if not found:
                return {"status": "error", "detail": f"Snippet '{original_trigger}' not found"}

            # Save back to file
            backup_dir = self._editor_backup_dir()
            backup_file = backup_dir / f"base.yml.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.bak"
            backup_file.write_text(base_file.read_text(encoding="utf-8"), encoding="utf-8")

            import yaml

            base_file.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            # Refresh and reload
            self.refresh_files()
            self.cli.run(["restart"])

            return {"status": "success", "detail": f"Updated snippet '{trigger}'"}
        except Exception as exc:
            return {"status": "error", "detail": f"Failed to update snippet: {exc}"}

    def delete_snippet(self, trigger: str) -> Dict[str, str]:
        """Delete a snippet from base.yml."""
        try:
            base_file = self._paths.match / "base.yml"

            if not base_file.exists():
                return {"status": "error", "detail": "base.yml not found"}

            data = self.yaml_processor.load(base_file)

            # Filter out the match
            original_count = len(data.get("matches", []))
            data["matches"] = [m for m in data.get("matches", []) if m.get("trigger") != trigger]

            if len(data["matches"]) == original_count:
                return {"status": "error", "detail": f"Snippet '{trigger}' not found"}

            # Save back to file
            import yaml
            backup_dir = self._editor_backup_dir()
            backup_file = backup_dir / f"base.yml.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.bak"
            backup_file.write_text(base_file.read_text(encoding="utf-8"), encoding="utf-8")

            base_file.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

            # Refresh and reload
            self.refresh_files()
            self.cli.run(["restart"])

            return {"status": "success", "detail": f"Deleted snippet '{trigger}'"}
        except Exception as exc:
            return {"status": "error", "detail": f"Failed to delete snippet: {exc}"}

    def get_snippet(self, trigger: str) -> Dict[str, Any]:
        """Get a single snippet by trigger for editing."""
        try:
            base_file = self._paths.match / "base.yml"

            if not base_file.exists():
                return {"status": "error", "detail": "base.yml not found"}

            data = self.yaml_processor.load(base_file)

            for match in data.get("matches", []):
                if match.get("trigger") == trigger:
                    return {
                        "status": "success",
                        "snippet": {
                            "trigger": match.get("trigger", ""),
                            "replace": match.get("replace", ""),
                            "word": match.get("word", False),
                            "propagate_case": match.get("propagate_case", False),
                            "vars": match.get("vars", []),
                            "form": match.get("form", ""),
                            "label": match.get("label", ""),
                            "enabled": match.get("enabled", True),
                            "backend": match.get("backend", ""),
                            "delay": self._sanitize_delay_value(match.get("delay")),
                            "left_word": match.get("left_word", False),
                            "right_word": match.get("right_word", False),
                            "uppercase_style": match.get("uppercase_style", ""),
                            "image_path": match.get("image_path", ""),
                        }
                    }

            return {"status": "error", "detail": f"Snippet '{trigger}' not found"}
        except Exception as exc:
            return {"status": "error", "detail": f"Failed to get snippet: {exc}"}

    def get_variable_types(self) -> List[Dict[str, Any]]:
        """Get all supported variable types with their metadata."""
        return [
            {
                "type": "date",
                "label": "Date/Time",
                "icon": "📅",
                "params": ["format", "offset"],
                "description": "Insert formatted timestamp with optional offsets.",
            },
            {
                "type": "clipboard",
                "label": "Clipboard",
                "icon": "📋",
                "params": ["fallback"],
                "description": "Expand to the current clipboard contents.",
            },
            {
                "type": "random",
                "label": "Random Choice",
                "icon": "🎲",
                "params": ["choices"],
                "description": "Pick a random option from a provided list.",
            },
            {
                "type": "shell",
                "label": "Shell Command",
                "icon": "💻",
                "params": ["cmd", "shell"],
                "description": "Execute a shell command and inject the output.",
            },
            {
                "type": "script",
                "label": "Script",
                "icon": "📜",
                "params": ["args"],
                "description": "Call an external script/binary with arguments.",
            },
            {
                "type": "echo",
                "label": "Echo Prompt",
                "icon": "💬",
                "params": ["prompt"],
                "description": "Prompt the user for free-form text when expanding.",
            },
            {
                "type": "choice",
                "label": "User Choice",
                "icon": "🎯",
                "params": ["values"],
                "description": "Present a list of options for the user to select.",
            },
            {
                "type": "form",
                "label": "Form Input",
                "icon": "📝",
                "params": ["fields"],
                "description": "Build multi-field forms for advanced snippets.",
            },
            {
                "type": "match",
                "label": "Match Reference",
                "icon": "🔗",
                "params": ["trigger"],
                "description": "Reference another match's output inline.",
            },
        ]

    def list_snippet_variables(self) -> List[Dict[str, Any]]:
        """Get all variables from all snippets for the variable library."""
        self._populate_matches()
        global_vars = []
        seen = set()

        for match in self._match_cache:
            var_list = match.get("vars") or match.get("variables") or []
            for var in var_list:
                name = var.get("name")
                var_type = var.get("type")
                if not name or not var_type:
                    continue
                var_key = f"{name}:{var_type}"
                if var_key in seen:
                    continue
                seen.add(var_key)
                global_vars.append({
                    "name": name,
                    "type": var_type,
                    "params": var.get("params", {}),
                    "source_snippet": match.get("trigger", "unknown")
                })

        return global_vars

    def create_backup(self) -> Dict[str, Any]:
        backup_dir = self._archive_backup_dir()
        payload = {
            "version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "matchFiles": [],
            "configFiles": [],
        }
        for file in self._paths.match.glob("*.yml"):
            payload["matchFiles"].append({"name": file.name, "content": file.read_text(encoding="utf-8")})
        if self._paths.config.exists():
            for child in self._paths.config.rglob("*.yml"):
                payload["configFiles"].append({"name": str(child.relative_to(self._paths.config)), "content": child.read_text(encoding="utf-8")})
        backup_file = backup_dir / f"espanso-backup-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.json"
        backup_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"path": str(backup_file), "count": len(payload["matchFiles"]) + len(payload["configFiles"])}

    def restart_espanso(self) -> Dict[str, Any]:
        result = self.cli.reload()
        return {"message": result.stdout.strip() or result.stderr.strip() or "Restart issued"}

    def get_feature_catalog(self) -> Dict[str, Any]:
        architecture = FeatureCatalog.describe_architecture()
        workflow = FeatureCatalog.describe_workflow()
        return {
            "architecture": [f"{section}: {', '.join(entries)}" for section, entries in architecture.items()],
            "requirements": _section_to_dict(FeatureCatalog.requirements),
            "workflow": {
                "title": "Workflow guidance",
                "items": self._build_workflow_items(workflow),
            },
            "integration": _section_to_dict(FeatureCatalog.integration_requirements),
            "ui": _section_to_dict(FeatureCatalog.ui_components),
            "variables": {
                "title": "Variable matrix",
                "types": [
                    f"{item['type']} ({item['editor']})"
                    for item in self.variable_engine.list_types()
                ],
                "methods": self.variable_engine.insertion_methods(),
                "insertionTitle": "Insertion methods",
            },
            "success": FeatureCatalog.success_criteria,
        }

    @staticmethod
    def _build_workflow_items(workflow: Dict[str, CatalogSection]) -> List[str]:
        items: List[str] = []
        for section in workflow.values():
            items.append(f"{section.title} — {section.description}")
            items.extend(section.items)
        return items


def _start_webview(window: Any, platform_info: PlatformInfo, script_path: Path) -> None:
    last_error: Optional[Exception] = None
    if platform_info.is_wsl:
        if _launch_windows_host_app(script_path):
            print("[INFO] Detected WSL. Launched EspansoGUI via Windows host process.", flush=True)
            return
        message = (
            "[ERROR] PyWebView cannot run inside WSL because no GUI subsystem is available, "
            "and launching the Windows host process failed. Install WSLg or run this script directly on Windows."
        )
        print(message, flush=True)
        raise webview.errors.WebViewException(message)  # type: ignore[attr-defined]

    for preferred in platform_info.gui_preferences():
        try:
            webview.start(gui=preferred, debug=True, http_server=False)
            return
        except webview.errors.WebViewException as exc:  # type: ignore[attr-defined]
            last_error = exc
            label = preferred or "auto"
            print(f"[WARNING] GUI backend '{label}' failed: {exc}", flush=True)
            continue
    print(
        "[ERROR] PyWebView could not initialize a GUI backend. "
        f"{platform_info.gui_dependency_hint()}",
        flush=True,
    )
    if last_error:
        raise last_error
    raise webview.errors.WebViewException("No GUI backend available")  # type: ignore[attr-defined]


def _launch_windows_host_app(script_path: Path) -> bool:
    """Launch the Windows version of this app when running inside WSL."""
    windows_script = _wsl_to_windows_path(script_path)
    windows_workdir = _wsl_to_windows_path(script_path.parent)
    powershell = Path("/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
    if not windows_script or not windows_workdir or not powershell.exists():
        return False
    for interpreter in ("py.exe", "python.exe"):
        ps_command = (
            f'Start-Process -FilePath "{interpreter}" '
            f'-ArgumentList "\\"{windows_script}\\"" '
            f'-WorkingDirectory "{windows_workdir}"'
        )
        result = subprocess.run(
            [str(powershell), "-NoProfile", "-Command", ps_command],
            check=False,
        )
        if result.returncode == 0:
            return True
    return False


def _wsl_to_windows_path(path: Path) -> Optional[str]:
    """Convert /mnt/<drive>/... paths into C:\\... form for Windows interop."""
    resolved = path.resolve()
    try:
        posix = PurePosixPath(resolved)
    except Exception:
        return None
    parts = posix.parts
    if len(parts) >= 4 and parts[0] == "/" and parts[1].lower() == "mnt":
        drive = parts[2].rstrip(":").upper()
        tail = PureWindowsPath(*parts[3:])
        win_path = PureWindowsPath(f"{drive}:/") / tail
        return str(win_path)
    return None


def main() -> None:
    api = EspansoAPI()
    html_path = Path(__file__).with_name("webview_ui") / "espanso_companion.html"
    script_path = Path(__file__).resolve()
    window = webview.create_window(
        "EspansoGUI",
        html=html_path.read_text(encoding="utf-8"),
        js_api=api,
        width=1360,
        height=900,
        min_size=(1000, 700),
    )
    _start_webview(window, api.platform, script_path)


if __name__ == "__main__":
    main()

"""
CHANGELOG
2025-02-14 Codex
- Added snippet validation, timezone-aware backups, and fixed global variable harvesting for the Snippet IDE.
- Enriched variable metadata so the frontend can render descriptive toolkit cards.
2025-11-14 Codex
- Added config override persistence, CLI-aware reinitialization, and config tree APIs plus watcher restarts for path explorer support.
2025-11-15 Codex
- CRITICAL FIX: Restored user's base.yml from backup after data loss
- PERFORMANCE FIX: Changed get_dashboard() to only populate cache once instead of on every call
- Added _ready flag to track initialization state
- Added _ensure_base_yaml() to create default template only when file is missing (never overwrites)
- Added informative logging throughout initialization and error paths
- Improved defensive checks in get_dashboard() and list_snippets()
2025-11-14 Codex
- Implemented Phase 5 snippet metadata CRUD (label, enable/disable, backend, delay, boundaries, uppercase, image) plus the server-side search API with filters.
2025-11-17 Codex
- Added Quick Insert backend helpers: image previews, shell command tester, and date offset preview APIs.
- Extended form snippet creation to support radio/select/checkbox inputs with validation.
2025-11-17 Codex
- Normalized global variable serialization to always emit Espanso's `type` field and drop incomplete entries.
2025-11-17 Codex
- Implemented pywebview GUI fallback logic so the app auto-detects supported backends and prints runtime installation tips when unavailable.
2025-11-17 Codex
- Added backend ping endpoint plus espanso match exec parsing so the dashboard bootstrap and match testing flows are reliable.
- Preserved Windows CRLF replacements when saving snippets to prevent truncated multi-line output.
2025-11-17 Codex
- Changed service health check to inspect `espanso status` before issuing redundant `start` commands so the daemon logs remain quiet while connected.
"""
