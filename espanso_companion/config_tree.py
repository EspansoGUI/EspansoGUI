"""Builds hierarchical config trees and import graphs for Espanso workspaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .yaml_processor import YamlProcessor


@dataclass
class ImportEdge:
    source: str
    target: str
    exists: bool
    resolved: str


@dataclass
class TreeNode:
    name: str
    path: str
    type: str
    children: List["TreeNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "children": [child.to_dict() for child in self.children],
        }


class ConfigTreeBuilder:
    """Summarizes the Espanso config/match directories plus import relationships."""

    def __init__(
        self,
        config_root: Path,
        match_root: Path,
        yaml_processor: Optional[YamlProcessor] = None,
    ):
        self._config_root = config_root
        self._match_root = match_root
        self._yaml = yaml_processor or YamlProcessor()

    def describe(self) -> Dict[str, Any]:
        """Return directory trees plus import diagnostics."""
        config_tree = self._build_directory_tree(self._config_root)
        match_tree = self._build_directory_tree(self._match_root)
        graph = self._build_import_graph()
        return {
            "configTree": config_tree.to_dict(),
            "matchTree": match_tree.to_dict(),
            "imports": {
                "edges": [edge.__dict__ for edge in graph["edges"]],
                "cycles": graph["cycles"],
                "missing": graph["missing"],
                "warnings": graph["warnings"],
            },
        }

    def _build_directory_tree(self, root: Path) -> TreeNode:
        if not root.exists():
            return TreeNode(name=root.name, path=str(root), type="missing", children=[])

        children: List[TreeNode] = []
        for child in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if child.is_dir():
                children.append(self._build_directory_tree(child))
            elif child.suffix.lower() in (".yml", ".yaml"):
                children.append(TreeNode(name=child.name, path=str(child), type="file"))

        return TreeNode(name=root.name, path=str(root), type="directory", children=children)

    def _build_import_graph(self) -> Dict[str, Any]:
        graph: Dict[str, List[Path]] = {}
        edges: List[ImportEdge] = []
        missing: List[str] = []
        warnings: List[str] = []

        for yaml_file in self._iter_yaml_files():
            try:
                data = self._yaml.load(yaml_file)
            except Exception as exc:
                warnings.append(f"Failed to parse {yaml_file.name}: {exc}")
                continue

            raw_entries = self._extract_import_entries(data)
            targets: List[Path] = []
            for entry in raw_entries:
                resolved = self._resolve_reference(yaml_file.parent, entry)
                targets.append(resolved)
                edge = ImportEdge(
                    source=self._relative_label(yaml_file),
                    target=self._relative_label(resolved),
                    exists=resolved.exists(),
                    resolved=str(resolved),
                )
                edges.append(edge)
                if not resolved.exists():
                    missing.append(edge.target)

            if targets:
                graph[str(yaml_file)] = targets

        cycles = self._detect_cycles(graph)
        return {
            "edges": edges,
            "cycles": cycles,
            "missing": missing,
            "warnings": warnings,
        }

    def _iter_yaml_files(self) -> Iterable[Path]:
        for root in (self._config_root, self._match_root):
            if not root.exists():
                continue
            yield from root.rglob("*.yml")
            yield from root.rglob("*.yaml")

    @staticmethod
    def _extract_import_entries(data: Dict[str, Any]) -> List[str]:
        entries: List[str] = []
        for key in ("imports", "includes"):
            raw = data.get(key)
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, str):
                        entries.append(item)
        return entries

    def _resolve_reference(self, base: Path, entry: str) -> Path:
        raw = entry.replace("$CONFIG", str(self._config_root))
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (base / raw).resolve()
        return candidate

    def _relative_label(self, path: Path) -> str:
        try:
            return str(path.relative_to(self._config_root))
        except ValueError:
            try:
                return str(path.relative_to(self._match_root))
            except ValueError:
                return str(path)

    def _detect_cycles(self, graph: Dict[str, List[Path]]) -> List[List[str]]:
        visited: Set[str] = set()
        stack: Set[str] = set()
        path_stack: List[str] = []
        cycles: List[List[str]] = []

        def dfs(node: str) -> None:
            visited.add(node)
            stack.add(node)
            path_stack.append(node)
            for neighbor in graph.get(node, []):
                neighbor_key = str(neighbor)
                if neighbor_key not in graph:
                    continue
                if neighbor_key not in visited:
                    dfs(neighbor_key)
                elif neighbor_key in stack:
                    cycle = self._cycle_slice(path_stack, neighbor_key)
                    if cycle:
                        cycles.append(cycle)
            path_stack.pop()
            stack.remove(node)

        for node in graph.keys():
            if node not in visited:
                dfs(node)

        return cycles

    def _cycle_slice(self, stack: List[str], start: str) -> List[str]:
        if start not in stack:
            return []
        start_index = stack.index(start)
        cycle_paths = stack[start_index:] + [start]
        return [self._relative_label(Path(path)) for path in cycle_paths]


"""
CHANGELOG
2025-11-14 Codex
- Added ConfigTreeBuilder to describe directory trees, import edges, and cycle diagnostics for Espanso configs.
"""
