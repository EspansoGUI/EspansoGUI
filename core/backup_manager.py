from __future__ import annotations

from pathlib import Path
from typing import Dict, List
import shutil
import json
from datetime import datetime


class BackupManager:
    """Simple backup manager for config directories.

    Provides manual backup creation, listing and basic restore helpers.
    """

    def __init__(self, backup_root: Path) -> None:
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def create_manual_backup(self, source_dir: Path, name: str | None = None) -> Dict[str, str]:
        if not source_dir.exists():
            return {"status": "error", "detail": "Source does not exist"}
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        backup_name = name or f"config_backup_{timestamp}"
        target = self.backup_root / backup_name
        try:
            shutil.copytree(source_dir, target)
            meta = {"version": "1.0", "timestamp": timestamp, "source": str(source_dir)}
            (target / "_backup_meta.json").write_text(json.dumps(meta), encoding="utf-8")
            return {"status": "success", "detail": f"Backup created: {backup_name}", "path": str(target)}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def list_backups(self) -> List[Dict[str, str]]:
        items = []
        for child in sorted(self.backup_root.iterdir(), reverse=True):
            if not child.is_dir():
                continue
            meta_file = child / "_backup_meta.json"
            meta = {}
            try:
                if meta_file.exists():
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
            items.append({"name": child.name, "path": str(child), "meta": meta})
        return items

    def restore_backup(self, backup_name: str, target_dir: Path, overwrite: bool = False) -> Dict[str, str]:
        src = self.backup_root / backup_name
        if not src.exists() or not src.is_dir():
            return {"status": "error", "detail": "Backup not found"}
        try:
            if target_dir.exists() and overwrite:
                shutil.rmtree(target_dir)
            if target_dir.exists() and not overwrite:
                return {"status": "error", "detail": "Target exists; set overwrite=True to replace"}
            shutil.copytree(src, target_dir)
            return {"status": "success", "detail": f"Restored to {target_dir}"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}
