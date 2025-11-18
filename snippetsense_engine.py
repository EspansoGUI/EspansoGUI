"""Background SnippetSense engine for detecting repetitive phrases."""

from __future__ import annotations

import hashlib
import platform
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Callable, Deque, Dict, List, Optional

try:
    from pynput import keyboard
except Exception:  # pragma: no cover - optional dependency
    keyboard = None  # type: ignore

try:
    import psutil
except Exception:  # pragma: no cover - optional dependency
    psutil = None  # type: ignore

try:
    import ctypes
    from ctypes import wintypes
except Exception:  # pragma: no cover
    ctypes = None  # type: ignore
    wintypes = None  # type: ignore


class SnippetSenseUnavailable(RuntimeError):
    """Raised when the engine cannot start due to missing dependencies."""


class SnippetSenseEngine:
    """Lightweight keystroke monitor that surfaces repeating phrases."""

    APP_DETECTION_SUPPORTED = (
        platform.system().lower() == "windows" and ctypes is not None and psutil is not None
    )

    WINDOW_SECONDS = 7 * 24 * 60 * 60  # rolling 7 days
    DEFAULT_IDLE_TIMEOUT = 30
    MAX_WORD_WINDOW = 6
    SUGGESTION_COOLDOWN = 600  # seconds between identical suggestions

    def __init__(self, suggestion_callback: Callable[[Dict[str, Any]], None]) -> None:
        self._callback = suggestion_callback
        self._listener: Optional[keyboard.Listener] = None  # type: ignore[assignment]
        self._running = False
        self._current_word: List[str] = []
        self._recent_words: Deque[str] = deque(maxlen=20)
        self._phrase_windows: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=40))
        self._suggested_at: Dict[str, float] = {}
        self._blocked_hashes: set[str] = set()
        self._handled_hashes: set[str] = set()
        self._settings: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._last_activity = time.time()
        self._app_detection_supported = self.APP_DETECTION_SUPPORTED

    @property
    def available(self) -> bool:
        return keyboard is not None  # type: ignore[arg-type]

    @property
    def app_detection_supported(self) -> bool:
        return self._app_detection_supported

    def start(self, settings: Dict[str, Any]) -> None:
        if not self.available:
            raise SnippetSenseUnavailable(
                "SnippetSense requires the 'pynput' package. Install with pip install pynput."
            )
        self.update_settings(settings)
        if self._listener:
            return
        self._running = True
        self._listener = keyboard.Listener(on_press=self._on_key_press)  # type: ignore[arg-type]
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        self._running = False
        listener = self._listener
        if listener:
            listener.stop()
        self._listener = None
        with self._lock:
            self._current_word.clear()
            self._recent_words.clear()
            self._phrase_windows.clear()

    def update_settings(self, settings: Dict[str, Any]) -> None:
        with self._lock:
            self._settings = {
                "enabled": bool(settings.get("enabled")),
                "min_words": max(1, int(settings.get("min_words", 3))),
                "min_chars": max(5, int(settings.get("min_chars", 10))),
                "repetition_threshold": max(2, int(settings.get("repetition_threshold", 3))),
                "whitelist": [item.lower() for item in settings.get("whitelist", []) if item],
                "blacklist": [item.lower() for item in settings.get("blacklist", []) if item],
                "blocked": settings.get("blocked", []),
                "idle_timeout": int(settings.get("idle_timeout", self.DEFAULT_IDLE_TIMEOUT)),
                "handled": settings.get("handled", []),
            }
            self._blocked_hashes = set(self._settings.get("blocked") or [])
            self._handled_hashes = set(self._settings.get("handled") or [])

    def _on_key_press(self, key: keyboard.Key) -> None:  # type: ignore[type-arg]
        if not self._running or not self._settings.get("enabled"):
            return
        if not self._is_allowed_target():
            return

        now = time.time()
        if now - self._last_activity > self._settings.get("idle_timeout", self.DEFAULT_IDLE_TIMEOUT):
            # Reset buffers after idle periods to avoid cross-sentence phrases
            with self._lock:
                self._current_word.clear()
                self._recent_words.clear()
        self._last_activity = now

        try:
            if hasattr(key, "char") and key.char:
                char = key.char
                if char.isprintable():
                    with self._lock:
                        self._current_word.append(char)
                return

            if key in (keyboard.Key.space, keyboard.Key.enter, keyboard.Key.tab):  # type: ignore[attr-defined]
                self._commit_word()
            elif key == keyboard.Key.backspace:  # type: ignore[attr-defined]
                with self._lock:
                    if self._current_word:
                        self._current_word.pop()
                    elif self._recent_words:
                        last_word = self._recent_words.pop()
                        self._current_word = list(last_word)
            else:
                name = getattr(key, "name", "")
                if name in {"period", "comma", "exclam", "question"}:
                    self._commit_word()
        except Exception:
            # Never allow keyboard hook failures to bubble up
            return

    def _commit_word(self) -> None:
        with self._lock:
            if self._current_word:
                word = "".join(self._current_word).strip()
                if word:
                    self._recent_words.append(word)
                self._current_word.clear()
        self._evaluate_recent_words()

    def _evaluate_recent_words(self) -> None:
        with self._lock:
            if not self._settings.get("enabled"):
                return
            min_words = self._settings.get("min_words", 3)
            min_chars = self._settings.get("min_chars", 10)
            words_snapshot = list(self._recent_words)
        max_window = min(self.MAX_WORD_WINDOW, len(words_snapshot))
        if max_window < min_words:
            return
        for size in range(min_words, max_window + 1):
            phrase_words = words_snapshot[-size:]
            phrase = " ".join(phrase_words).strip()
            if len(phrase) < min_chars:
                continue
            self._register_phrase(phrase)

    def _register_phrase(self, phrase: str) -> None:
        payload: Optional[Dict[str, Any]] = None
        with self._lock:
            key = hashlib.sha256(phrase.lower().encode("utf-8")).hexdigest()
            if key in self._blocked_hashes or key in self._handled_hashes:
                return
            now = time.time()
            window = self._phrase_windows[key]
            window.append(now)
            cutoff = now - self.WINDOW_SECONDS
            while window and window[0] < cutoff:
                window.popleft()
            count = len(window)
            if count < self._settings.get("repetition_threshold", 3):
                return
            last_suggested = self._suggested_at.get(key, 0)
            if now - last_suggested < self.SUGGESTION_COOLDOWN:
                return
            self._suggested_at[key] = now
            payload = {
                "hash": key,
                "phrase": phrase,
                "count": count,
                "timestamp": datetime.utcnow().isoformat(),
            }
        if not payload:
            return
        try:
            self._callback(payload)
        except Exception:
            # Keep engine alive even if callback fails
            pass

    def _is_allowed_target(self) -> bool:
        if not self._app_detection_supported:
            return True
        whitelist = self._settings.get("whitelist") or []
        blacklist = self._settings.get("blacklist") or []
        app_name = self._get_active_app_name()
        if whitelist:
            if not app_name:
                return False
            return any(app_name.startswith(entry) for entry in whitelist)
        if app_name and any(app_name.startswith(entry) for entry in blacklist):
            return False
        return True

    def _get_active_app_name(self) -> Optional[str]:
        if not self._app_detection_supported:
            return None
        if ctypes is None or psutil is None:  # pragma: no cover
            return None
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return None
        try:
            name = psutil.Process(pid.value).name()
            return (name or "").lower()
        except Exception:
            return None

"""
CHANGELOG
2025-11-17 Codex
- Added thread-safe deduplication for SnippetSense suggestions, honoring handled hashes and skipping repeats.
- Ensured phrase evaluation copies keystrokes in-order to prevent shuffled replacements and emits callbacks outside locks.
2025-11-17 Codex
- Enabled SnippetSense on macOS/Linux by degrading app whitelist/blacklist when OS-level window detection is unavailable.
"""
