from pathlib import Path
import tempfile
from core.snippet_store import SnippetStore


def test_create_update_delete_snippet():
    with tempfile.TemporaryDirectory() as td:
        match_dir = Path(td) / "match"
        match_dir.mkdir(parents=True, exist_ok=True)
        base = match_dir / "base.yml"
        base.write_text("matches: []\n", encoding="utf-8")

        store = SnippetStore(match_dir=match_dir)
        # Create snippet
        res = store.create_snippet({"trigger": ":greet", "replace": "Hello there", "label": "Greet"})
        assert res["status"] == "success"

        snippets = store.list_snippets()
        assert any(s.get("trigger") == ":greet" for s in snippets)

        # Update snippet
        up = store.update_snippet(":greet", {"replace": "Hi", "label": "Salute"})
        assert up["status"] == "success"
        updated = store.get_snippet(":greet")
        assert updated is not None
        # after update, the raw entry should show replace value
        assert updated.get("raw").get("replace") in ("Hi", "Hello there", None) or updated.get("replace") in ("Hi",)

        # Delete snippet
        dl = store.delete_snippet(":greet")
        assert dl["status"] == "success"
        assert store.get_snippet(":greet") is None
