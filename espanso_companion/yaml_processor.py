"""YAML parsing and validation helpers used by the IDE."""

from __future__ import annotations

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


class YamlProcessor:
    """Wraps safe loading/dumping plus lightweight validation."""

    def load(self, source: Path) -> Dict[str, Any]:
        """Load YAML from disk and return a dict."""
        with source.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return self._normalize(data)

    def load_str(self, text: str) -> Dict[str, Any]:
        """Load YAML content from a string."""
        data = yaml.safe_load(text) or {}
        return self._normalize(data)

    def dump(self, data: Dict[str, Any], target: Path, *, schema_version: Optional[str] = None) -> None:
        """Persist YAML while preserving order and optional schema metadata."""
        if schema_version:
            data.setdefault("schema_version", schema_version)
        with target.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, sort_keys=False)

    def validate(self, data: Dict[str, Any], required_keys: Sequence[str]) -> Tuple[bool, List[str]]:
        """Check for required keys, return (ok, missing)."""
        missing = [key for key in required_keys if key not in data]
        return (not missing), missing

    def flatten_matches(self, data: Dict[str, Any]) -> List["MatchDefinition"]:
        """Transform nested matches into normalized dataclasses for the UI."""
        matches: List[MatchDefinition] = []
        match_list = data.get("matches") or []
        for raw in match_list:
            matches.append(
                MatchDefinition(
                    name=raw.get("name", ""),
                    trigger=raw.get("trigger", ""),
                    replace=raw.get("replace", ""),
                    variables=raw.get("vars", []),
                    enabled=raw.get("enabled", True),
                    meta=raw.get("meta", {}),
                    label=raw.get("label", ""),
                    backend=raw.get("backend", ""),
                    delay=raw.get("delay"),
                    left_word=bool(raw.get("left_word", False)),
                    right_word=bool(raw.get("right_word", False)),
                    uppercase_style=raw.get("uppercase_style", ""),
                    image_path=raw.get("image_path", ""),
                    word=bool(raw.get("word", False)),
                    propagate_case=bool(raw.get("propagate_case", False)),
                    form=raw.get("form"),
                )
            )
        return matches

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data if isinstance(data, dict) else {}


@dataclass
class MatchDefinition:
    name: str
    trigger: str
    replace: str
    variables: List[Dict[str, Any]]
    enabled: bool = True
    meta: Dict[str, Any] = None
    label: str = ""
    backend: str = ""
    delay: Optional[Any] = None
    left_word: bool = False
    right_word: bool = False
    uppercase_style: str = ""
    image_path: str = ""
    word: bool = False
    propagate_case: bool = False
    form: Any = None

"""
CHANGELOG
2025-11-14 Codex
- Added support for Phase 5 snippet fields (label, backend, delay, word boundaries, uppercase style, image path) to keep match normalization aligned with Espanso's schema.
"""
