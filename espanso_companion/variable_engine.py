"""Variable management layer bridging the word processor UI and Espanso runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


VARIABLE_TYPES = [
    {"type": "text", "editor": "rich_text"},
    {"type": "date", "editor": "calendar_with_formats"},
    {"type": "time", "editor": "time_selector_with_zones"},
    {"type": "number", "editor": "calculator_interface"},
    {"type": "choice", "editor": "visual_dropdown_builder"},
    {"type": "list", "editor": "spreadsheet_interface"},
    {"type": "script", "editor": "code_editor_with_preview"},
    {"type": "api", "editor": "rest_client_builder"},
    {"type": "file", "editor": "file_picker_with_preview"},
    {"type": "image", "editor": "image_editor_with_crop"},
]

INSERTION_METHODS = [
    "double_brace_trigger",
    "tab_completion",
    "right_click_context",
    "drag_drop_palette",
    "voice_commands",
    "markdown_shortcuts",
]


@dataclass
class VariableDefinition:
    name: str
    type: str
    editor: str
    params: Dict[str, Any]


class VariableEngine:
    """Provides metadata for inline variable editing and previews."""

    def __init__(self) -> None:
        self._type_lookup: Dict[str, Dict[str, Any]] = {v["type"]: v for v in VARIABLE_TYPES}

    def list_types(self) -> List[Dict[str, Any]]:
        return VARIABLE_TYPES

    def describe_type(self, type_name: str) -> Dict[str, Any]:
        return self._type_lookup.get(type_name, {})

    def build_variable(self, name: str, type_name: str, params: Dict[str, Any]) -> VariableDefinition:
        editor = self._type_lookup.get(type_name, {}).get("editor", "rich_text")
        return VariableDefinition(name=name, type=type_name, editor=editor, params=params)

    def preview(self, variable: VariableDefinition) -> str:
        if variable.type == "text":
            return variable.params.get("value", "")
        if variable.type == "choice":
            return variable.params.get("selected", "") or next(iter(variable.params.get("options", [])), "")
        if variable.type == "date":
            return variable.params.get("format", "%Y-%m-%d")
        return f"<{variable.type}>"

    def insertion_methods(self) -> List[str]:
        return INSERTION_METHODS
