from pathlib import Path
from core.config_manager import ConfigManager
import tempfile


def test_preferences_read_write():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "profile"
        cm = ConfigManager(base_dir=base)
        # initially empty
        prefs = cm.get_preferences()
        assert isinstance(prefs, dict)

        cm.set_preference("foo", "bar")
        loaded = cm.get_preferences()
        assert loaded.get("foo") == "bar"

        # data root resolves and is inside base
        data_root = cm.get_data_root()
        assert isinstance(data_root, Path)
        assert str(base) in str(data_root)

        # ensure base yaml creation does not raise
        match_dir = Path(td) / "match"
        cm.ensure_base_yaml(match_dir)
        assert (match_dir / "base.yml").exists()
