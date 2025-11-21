from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import yaml


class VariableManager:
    """Manages global variables in Espanso base.yml configuration.

    Provides CRUD operations for global_vars entries with proper
    normalization and serialization.
    """

    def __init__(self, match_dir: Path) -> None:
        self.match_dir = Path(match_dir)
        self.base_file = self.match_dir / "base.yml"

    def get_all(self) -> Dict[str, Any]:
        """Get all global variables from base config."""
        try:
            if not self.base_file.exists():
                return {"status": "success", "variables": []}

            with open(self.base_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            normalized: List[Dict[str, Any]] = []
            for raw in data.get("global_vars", []) or []:
                item = dict(raw or {})
                var_type = item.get("type") or item.get("var_type") or ""
                name = item.get("name", "")
                params = item.get("params") or {}
                normalized.append({
                    "name": name,
                    "type": var_type,
                    "params": params,
                })
            return {"status": "success", "variables": normalized}
        except Exception as e:
            return {"status": "error", "variables": [], "detail": str(e)}

    def update_all(self, variables: list) -> Dict[str, str]:
        """Update all global variables in base config (full replacement)."""
        try:
            if not self.base_file.exists():
                return {"status": "error", "detail": "base.yml not found"}

            with open(self.base_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            sanitized: List[Dict[str, Any]] = []
            for item in variables or []:
                name = (item.get("name") or "").strip()
                var_type = (item.get("type") or item.get("var_type") or "").strip()
                if not name or not var_type:
                    continue
                entry: Dict[str, Any] = {"name": name, "type": var_type}
                params = item.get("params") or {}
                if params:
                    entry["params"] = params
                sanitized.append(entry)

            data["global_vars"] = sanitized

            with open(self.base_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            return {"status": "success", "detail": "Global variables updated"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def add(self, name: str, var_type: str, params: Dict[str, Any] | None = None) -> Dict[str, str]:
        """Add a single global variable."""
        result = self.get_all()
        if result.get("status") != "success":
            return {"status": "error", "detail": result.get("detail", "Failed to read variables")}

        variables = result.get("variables", [])
        # Check for duplicate name
        if any(v.get("name") == name for v in variables):
            return {"status": "error", "detail": f"Variable '{name}' already exists"}

        variables.append({
            "name": name,
            "type": var_type,
            "params": params or {},
        })
        return self.update_all(variables)

    def update(self, name: str, var_type: str, params: Dict[str, Any] | None = None) -> Dict[str, str]:
        """Update an existing global variable by name."""
        result = self.get_all()
        if result.get("status") != "success":
            return {"status": "error", "detail": result.get("detail", "Failed to read variables")}

        variables = result.get("variables", [])
        found = False
        for v in variables:
            if v.get("name") == name:
                v["type"] = var_type
                v["params"] = params or {}
                found = True
                break

        if not found:
            return {"status": "error", "detail": f"Variable '{name}' not found"}

        return self.update_all(variables)

    def delete(self, name: str) -> Dict[str, str]:
        """Delete a global variable by name."""
        result = self.get_all()
        if result.get("status") != "success":
            return {"status": "error", "detail": result.get("detail", "Failed to read variables")}

        variables = result.get("variables", [])
        original_count = len(variables)
        variables = [v for v in variables if v.get("name") != name]

        if len(variables) == original_count:
            return {"status": "error", "detail": f"Variable '{name}' not found"}

        return self.update_all(variables)
