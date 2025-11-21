from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional
import threading
import time

from espanso_companion.file_watcher import FileWatcher, WatchEvent


class WatcherManager:
    """Manage a FileWatcher instance with safe start/stop and callback registration.

    Accepts an optional `watcher` for testing injection. When not provided the
    real `FileWatcher` is used.
    """

    def __init__(self, paths: List[Path], watcher: Optional[FileWatcher] = None) -> None:
        self._paths = list(paths)
        self._watcher = watcher or FileWatcher(self._paths)
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        try:
            self._watcher.start()
            self._started = True
        except Exception:
            # Fail silently; caller can check poll_events to see activity
            self._started = False

    def stop(self) -> None:
        if not self._started:
            return
        try:
            self._watcher.stop()
        except Exception:
            pass
        finally:
            self._started = False

    def register_callback(self, callback: Callable[[WatchEvent], None]) -> None:
        try:
            self._watcher.register_callback(callback)
        except Exception:
            # if watcher implementation doesn't support callbacks, ignore
            pass

    def poll_events(self) -> List[WatchEvent]:
        try:
            return self._watcher.poll()
        except Exception:
            return []

    def is_running(self) -> bool:
        return self._started
