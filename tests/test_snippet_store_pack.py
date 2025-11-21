import json
import tempfile

from pathlib import Path

from core.snippet_store import SnippetStore


def test_import_snippet_pack():
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        match_dir = tmp_path / "match"
        match_dir.mkdir()
        pack = [
            {"trigger": ":alpha", "replace": "Alpha"},
            {"trigger": ":beta", "replace": "Beta"},
        ]
        pack_path = tmp_path / "pack.json"
        pack_path.write_text(json.dumps(pack), encoding="utf-8")

        store = SnippetStore(match_dir=match_dir)
        result = store.import_snippet_pack(str(pack_path))
        assert result["status"] == "success"
        snippets = store.list_snippets()
        assert any(s["trigger"] == ":alpha" for s in snippets)
        assert any(s["trigger"] == ":beta" for s in snippets)

        export_path = tmp_path / "export.json"
        export_result = store.export_snippet_pack([":alpha", ":beta"], str(export_path))
        assert export_result["status"] == "success"
        exported = json.loads(export_path.read_text(encoding="utf-8"))
        assert len(exported) == 2
        assert all(entry.get("trigger") in {":alpha", ":beta"} for entry in exported)
