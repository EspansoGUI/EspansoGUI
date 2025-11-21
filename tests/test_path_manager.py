from core.path_manager import PathManager
from pathlib import Path
import tempfile


class DummyLoader:
    def __init__(self, paths):
        self._paths = paths

    def discover_paths(self, override):
        return self._paths


def test_path_manager_injection():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        dummy = DummyLoader({"config": base / "config", "match": base / "match"})
        pm = PathManager(loader=dummy)
        paths = pm.get_paths()
        assert paths == dummy._paths
        new = pm.discover_paths(str(base / 'override'))
        assert new == dummy._paths
