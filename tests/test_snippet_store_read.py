from pathlib import Path
import tempfile
from core.snippet_store import SnippetStore


def test_snippet_listing_and_search():
    with tempfile.TemporaryDirectory() as td:
        match_dir = Path(td) / "match"
        match_dir.mkdir(parents=True, exist_ok=True)
        # Create two simple YAML match files
        f1 = match_dir / "base.yml"
        f1.write_text(
            """matches:
  - trigger: ":hello"
    replace: "Hello"
  - trigger: ":bye"
    replace: "Goodbye"
""",
            encoding="utf-8",
        )
        f2 = match_dir / "extras.yml"
        f2.write_text(
            """matches:
  - trigger: ":email"
    replace: "you@example.com"
""",
            encoding="utf-8",
        )

        store = SnippetStore(match_dir=match_dir)
        snippets = store.list_snippets()
        assert len(snippets) == 3

        found = store.get_snippet(":hello")
        assert found is not None
        assert found.get("trigger") == ":hello"

        search_result = store.search_snippets("hello")
        assert search_result["count"] == 1
        assert search_result["results"][0]["trigger"] == ":hello"
