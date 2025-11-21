from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
import threading
import time


class SnippetSenseAdapter:
    """Adapter that manages an optional SnippetSense engine and a pending suggestions queue.

    This adapter is intentionally minimal: it accepts an `engine` object that should
    provide `start(callback, settings)`, `stop()` and `update_settings(settings)` methods
    (the real `SnippetSenseEngine` in the project), but for tests a fake engine may be
    injected. The adapter stores pending suggestions in-memory and exposes methods to
    list and decide on them. On `accept` it will call `snippet_creator` if provided.
    """

    def __init__(
        self,
        engine: Optional[Any] = None,
        settings: Optional[Dict[str, Any]] = None,
        snippet_creator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> None:
        self._engine = engine
        self._settings = settings or {}
        self._pending: List[Dict[str, Any]] = []
        self._pending_lock = threading.Lock()
        self._blocked: set = set(self._settings.get("blocked") or [])
        self._handled: set = set(self._settings.get("handled") or [])
        self._snippet_creator = snippet_creator

    def available(self) -> bool:
        return self._engine is not None

    def start(self, settings: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        self._settings.update(settings or {})
        # reload blocked/handled from settings
        self._blocked = set(self._settings.get("blocked") or [])
        self._handled = set(self._settings.get("handled") or [])
        if not self._engine:
            return False, "engine_not_available"
        try:
            # Engine expected to accept a callback
            start_fn = getattr(self._engine, "start", None)
            if start_fn is None:
                return False, "engine_missing_start"
            # Provide the adapter's suggestion handler
            start_fn(self._on_suggestion, self._settings)
            return True, None
        except Exception as exc:
            return False, str(exc)

    def stop(self) -> None:
        if not self._engine:
            return
        stop_fn = getattr(self._engine, "stop", None)
        if stop_fn:
            try:
                stop_fn()
            except Exception:
                pass

    def update_settings(self, settings: Dict[str, Any]) -> None:
        self._settings.update(settings or {})
        self._blocked = set(self._settings.get("blocked") or [])
        self._handled = set(self._settings.get("handled") or [])
        if self._engine:
            update_fn = getattr(self._engine, "update_settings", None)
            if update_fn:
                try:
                    update_fn(self._settings)
                except Exception:
                    pass

    def _on_suggestion(self, payload: Dict[str, Any]) -> None:
        """Internal callback invoked by engine when a suggestion is available."""
        # Expected payload keys: hash, phrase, count, timestamp
        suggestion_hash = payload.get("hash")
        if not suggestion_hash:
            return
        # Ignore blocked or handled
        if suggestion_hash in self._blocked or suggestion_hash in self._handled:
            return
        with self._pending_lock:
            hashes = {item.get("hash") for item in self._pending}
            if suggestion_hash in hashes:
                return
            item = {
                "id": f"ss_{int(time.time()*1000)}",
                "hash": suggestion_hash,
                "phrase": payload.get("phrase") or "",
                "count": payload.get("count") or 0,
                "created": payload.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            self._pending.append(item)

    def list_pending(self) -> List[Dict[str, Any]]:
        with self._pending_lock:
            return list(self._pending)

    def handle_decision(self, suggestion_id: str, decision: str) -> Dict[str, Any]:
        decision = (decision or "").lower()
        if decision not in {"accept", "reject", "never"}:
            return {"status": "error", "detail": f"Unsupported decision: {decision}"}

        suggestion = None
        with self._pending_lock:
            for item in self._pending:
                if item.get("id") == suggestion_id:
                    suggestion = item
                    break
            if not suggestion:
                return {"status": "error", "detail": "Suggestion not found"}
            # remove from pending
            self._pending = [i for i in self._pending if i.get("id") != suggestion_id]

        phrase_hash = suggestion.get("hash")
        phrase = suggestion.get("phrase") or ""

        if decision == "accept":
            # Create snippet via provided creator function if available
            if self._snippet_creator:
                try:
                    trigger = self._generate_trigger(phrase)
                    payload = {"trigger": trigger, "replace": phrase, "label": "SnippetSense"}
                    created = self._snippet_creator(payload)
                except Exception as exc:
                    return {"status": "error", "detail": f"Create failed: {exc}"}
            # mark handled
            if phrase_hash:
                self._handled.add(phrase_hash)
            return {"status": "success", "detail": "Accepted", "trigger": created.get("trigger") if self._snippet_creator else None}

        if decision == "never":
            if phrase_hash:
                self._blocked.add(phrase_hash)
            if phrase_hash:
                self._handled.add(phrase_hash)
            return {"status": "success", "detail": "Phrase blocked"}

        # reject
        if phrase_hash:
            self._handled.add(phrase_hash)
        return {"status": "success", "detail": "Suggestion dismissed"}

    def _generate_trigger(self, phrase: str) -> str:
        cleaned = "".join(ch for ch in phrase.lower() if ch.isalnum() or ch.isspace()).strip()
        words = cleaned.split()
        if not words:
            words = ["snippet"]
        base = ":" + "".join(word[:2] for word in words)[:6]
        if len(base) < 3:
            base = ":ss" + cleaned.replace(" ", "")[:3]
        # naive uniqueness: append timestamp
        return f"{base}{int(time.time())}"
