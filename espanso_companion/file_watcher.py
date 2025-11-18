"""Filesystem watching helpers for real-time UI updates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from typing import Callable, List

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


@dataclass
class WatchEvent:
    src_path: Path
    event_type: str
    is_directory: bool


class _EventHandler(FileSystemEventHandler):
    def __init__(self, queue: Queue):
        super().__init__()
        self._queue = queue

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle filesystem events with error protection."""
        try:
            if not event.src_path:
                return
            self._queue.put(
                WatchEvent(
                    src_path=Path(event.src_path),
                    event_type=event.event_type,
                    is_directory=event.is_directory,
                )
            )
        except Exception:
            # Silently ignore errors in event handler to prevent watcher thread crash
            # This can happen with invalid paths, permissions issues, etc.
            pass


class FileWatcher:
    """Observes directories and exposes pending events for polling."""

    def __init__(self, paths: List[Path]) -> None:
        self._queue: Queue = Queue()
        self._observer = Observer()
        self._handler = _EventHandler(self._queue)
        self._paths = paths
        self._callbacks: List[Callable[[WatchEvent], None]] = []

    def start(self) -> None:
        for path in self._paths:
            self._observer.schedule(self._handler, str(path), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=1)

    def register_callback(self, callback: Callable[[WatchEvent], None]) -> None:
        self._callbacks.append(callback)

    def poll(self) -> List[WatchEvent]:
        """Drain pending events for the UI layer to consume."""
        events: List[WatchEvent] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except Empty:
                break
        return events
