from core.backup_manager import BackupManager
from pathlib import Path
import tempfile


def test_backup_create_and_list_and_restore():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / "config"
        src.mkdir()
        (src / "a.txt").write_text("hello", encoding="utf-8")

        backup_root = base / "backups"
        bm = BackupManager(backup_root)
        res = bm.create_manual_backup(src)
        assert res["status"] == "success"
        path = Path(res["path"])
        assert path.exists()
        assert (path / "a.txt").exists()

        items = bm.list_backups()
        assert any(item["name"] == path.name for item in items)

        # restore to new target
        tgt = base / "restore"
        rt = bm.restore_backup(path.name, tgt)
        assert rt["status"] == "success"
        assert (tgt / "a.txt").exists()
