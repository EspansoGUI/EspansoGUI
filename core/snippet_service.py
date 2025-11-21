from __future__ import annotations

from typing import Any, Dict, List, Optional


class SnippetService:
    def __init__(self, snippet_store: Any, cli: Any):
        self._store = snippet_store
        self._cli = cli

    def create_snippet(self, snippet_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._store.create_snippet(snippet_data)
        if result.get("status") == "success":
            try:
                self._cli.run(["restart"])
            except Exception:  # pragma: no cover - best effort
                pass
        return result

    def update_snippet(self, original_trigger: str, snippet_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._store.update_snippet(original_trigger, snippet_data)

    def delete_snippet(self, trigger: str) -> Dict[str, Any]:
        return self._store.delete_snippet(trigger)

    def list_snippets(self) -> List[Dict[str, Any]]:
        return self._store.list_snippets()

    def search_snippets(self, query: str = "", filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._store.search_snippets(query, filters)
