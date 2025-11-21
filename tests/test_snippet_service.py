from core.snippet_service import SnippetService


class DummyStore:
    def __init__(self):
        self.calls = []
        self.snippets = []

    def create_snippet(self, data):
        self.calls.append(("create", data))
        self.snippets.append(data)
        return {"status": "success", "detail": "created"}

    def update_snippet(self, trigger, data):
        self.calls.append(("update", trigger, data))
        return {"status": "success"}

    def delete_snippet(self, trigger):
        self.calls.append(("delete", trigger))
        return {"status": "success"}

    def list_snippets(self):
        self.calls.append(("list",))
        return self.snippets

    def search_snippets(self, query, filters):
        self.calls.append(("search", query, filters))
        return {"status": "success"}


class DummyCLI:
    def __init__(self):
        self.commands = []

    def run(self, args):
        self.commands.append(tuple(args))
        class _Result:
            stdout = ""
            stderr = ""
            returncode = 0
        return _Result()


def test_snippet_service_restart():
    store = DummyStore()
    cli = DummyCLI()
    service = SnippetService(store, cli)
    result = service.create_snippet({"trigger": ":foo", "replace": "bar"})
    assert result["status"] == "success"
    assert ("restart",) in cli.commands

    service.update_snippet(":foo", {"replace": "baz"})
    assert ("update", ":foo", {"replace": "baz"}) in store.calls

    service.delete_snippet(":foo")
    assert ("delete", ":foo") in store.calls
