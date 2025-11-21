from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pathlib import Path


class SnippetStore:
    """Read-only snippet storage & simple search over Espanso `match` YAML files.

    This is an intentionally small, testable first step: populate and search snippets.
    """

    def __init__(self, match_dir: Optional[Path] = None) -> None:
        self.match_dir = Path(match_dir) if match_dir is not None else None
        self._match_cache: List[Dict[str, Any]] = []
        self._yaml_errors: List[Dict[str, Any]] = []

    def set_match_dir(self, path: Path) -> None:
        self.match_dir = path

    def list_snippets(self) -> List[Dict[str, Any]]:
        if not self._match_cache:
            self._populate_matches()
        return list(self._match_cache)

    def _populate_matches(self) -> None:
        matches: List[Dict[str, Any]] = []
        yaml_errors: List[Dict[str, Any]] = []

        if not self.match_dir or not self.match_dir.exists():
            self._match_cache = matches
            self._yaml_errors = yaml_errors
            return

        yaml_files = list(self.match_dir.glob("*.yml"))
        for file in yaml_files:
            try:
                content = file.read_text(encoding="utf-8")
                data = yaml.safe_load(content) or {}
            except Exception as exc:
                yaml_errors.append({"file": str(file), "error": str(exc)})
                continue

            try:
                # Espanso defines top-level `matches` as a list
                for raw in (data.get("matches") or []):
                    trigger = None
                    replace = None
                    label = raw.get("label") if isinstance(raw, dict) else None
                    if isinstance(raw, dict):
                        trigger = raw.get("trigger")
                        replace = raw.get("replace")
                    # Some match entries may be nested or different shapes; skip if no trigger
                    if not trigger:
                        continue
                    matches.append(
                        {
                            "trigger": trigger,
                            "replace": replace,
                            "file": file.name,
                            "label": label or "",
                            "raw": raw,
                        }
                    )
            except Exception as exc:
                yaml_errors.append({"file": str(file), "error": str(exc)})

        self._match_cache = matches
        self._yaml_errors = yaml_errors

    def get_snippet(self, trigger: str) -> Optional[Dict[str, Any]]:
        if not self._match_cache:
            self._populate_matches()
        for s in self._match_cache:
            if s.get("trigger") == trigger:
                return s
        return None

    def search_snippets(self, query: str = "", filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        filters = filters or {}
        results: List[Dict[str, Any]] = []
        if not self._match_cache:
            self._populate_matches()
        q = (query or "").strip().lower()

        for s in self._match_cache:
            trigger = (s.get("trigger") or "").lower()
            replace = (s.get("replace") or "")
            file = (s.get("file") or "")
            label = (s.get("label") or "")

            if q:
                if q in trigger or q in replace.lower() or q in label.lower():
                    results.append(s)
                else:
                    continue
            else:
                results.append(s)

        return {"status": "success", "count": len(results), "results": results}

    # -------------------------
    # Write operations (CRUD)
    # -------------------------
    def _write_matches_file(self, path: Path, data: Dict[str, Any]) -> None:
        try:
            path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        except Exception:
            # bubble up on failure in higher-level methods
            raise

    def _load_snippet_file(self, file_path: Path) -> List[Dict[str, Any]]:
        if not file_path.exists():
            return []
        try:
            data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return []
        return data.get("matches") or []

    def create_snippet(self, snippet_data: Dict[str, Any]) -> Dict[str, str]:
        """Create a snippet in `base.yml` (creates file if missing).

        Minimal behavior: appends the snippet dict into the top-level `matches` list
        and clears the internal cache so subsequent reads pick up changes.
        """
        if not self.match_dir:
            return {"status": "error", "detail": "Match directory not configured"}
        base_file = self.match_dir / "base.yml"
        try:
            if base_file.exists():
                content = yaml.safe_load(base_file.read_text(encoding="utf-8")) or {}
            else:
                content = {}
            matches = content.get("matches") or []
            # Build the entry we will append
            entry = {}
            if "trigger" in snippet_data:
                entry["trigger"] = snippet_data["trigger"]
            if "replace" in snippet_data:
                entry["replace"] = snippet_data["replace"]
            if "label" in snippet_data:
                entry["label"] = snippet_data["label"]
            matches.append(entry)
            content["matches"] = matches
            self._write_matches_file(base_file, content)
            # Invalidate cache
            self._match_cache = []
            return {"status": "success", "detail": f"Created snippet {entry.get('trigger') or ''}"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def update_snippet(self, original_trigger: str, snippet_data: Dict[str, Any]) -> Dict[str, str]:
        """Locate the first snippet with `original_trigger` and update its fields.

        Returns an error if the snippet cannot be found.
        """
        if not self.match_dir:
            return {"status": "error", "detail": "Match directory not configured"}
        try:
            # Search all YAML files for the snippet
            for file in self.match_dir.glob("*.yml"):
                try:
                    data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
                except Exception:
                    continue
                changed = False
                matches = data.get("matches") or []
                for item in matches:
                    if isinstance(item, dict) and item.get("trigger") == original_trigger:
                        # apply updates
                        for k, v in snippet_data.items():
                            if v is None:
                                item.pop(k, None)
                            else:
                                item[k] = v
                        changed = True
                        break
                if changed:
                    data["matches"] = matches
                    self._write_matches_file(file, data)
                    self._match_cache = []
                    return {"status": "success", "detail": f"Updated {original_trigger}"}
            return {"status": "error", "detail": "Snippet not found"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def delete_snippet(self, trigger: str) -> Dict[str, str]:
        """Delete a snippet identified by `trigger` from the first file that contains it."""
        if not self.match_dir:
            return {"status": "error", "detail": "Match directory not configured"}
        try:
            for file in self.match_dir.glob("*.yml"):
                try:
                    data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
                except Exception:
                    continue
                matches = data.get("matches") or []
                new_matches = [m for m in matches if not (isinstance(m, dict) and m.get("trigger") == trigger)]
                if len(new_matches) != len(matches):
                    data["matches"] = new_matches
                    self._write_matches_file(file, data)
                    self._match_cache = []
                    return {"status": "success", "detail": f"Deleted {trigger}"}
            return {"status": "error", "detail": "Snippet not found"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def import_snippet_pack(self, file_path: str) -> Dict[str, Any]:
        """Import snippets from a JSON or YAML snippet pack."""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"status": "error", "detail": "File not found"}
            if path.suffix.lower() == ".json":
                import json

                packs = json.loads(path.read_text(encoding="utf-8"))
            else:
                packs = yaml.safe_load(path.read_text(encoding="utf-8"))

            if isinstance(packs, dict):
                packs = packs.get("matches", [])
            if not isinstance(packs, list):
                return {"status": "error", "detail": "Invalid pack format"}

            count = 0
            for snippet in packs:
                if isinstance(snippet, dict) and snippet.get("trigger"):
                    res = self.create_snippet(snippet)
                    if res.get("status") == "success":
                        count += 1
            return {"status": "success", "detail": f"Imported {count} snippets"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def export_snippet_pack(self, triggers: List[str], file_path: str) -> Dict[str, Any]:
        """Export the selected snippets to a JSON file."""
        snippets: List[Dict[str, Any]] = []
        for trigger in triggers:
            snippet = self.get_snippet(trigger)
            if snippet:
                snippets.append(snippet.get("raw") or snippet)
        try:
            import json

            Path(file_path).write_text(json.dumps(snippets, indent=2, ensure_ascii=False), encoding="utf-8")
            return {"status": "success", "detail": f"Exported {len(snippets)} snippets", "path": file_path}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}
