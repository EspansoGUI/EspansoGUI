from core.snippetsense_adapter import SnippetSenseAdapter


class FakeEngine:
    def __init__(self):
        self._cb = None
        self.started = False

    def start(self, callback, settings):
        self._cb = callback
        self.started = True

    def stop(self):
        self.started = False

    def update_settings(self, settings):
        pass

    # helper to simulate suggestion
    def simulate(self, payload):
        if self._cb:
            self._cb(payload)


def test_pending_and_decision_flow():
    engine = FakeEngine()
    created_snippets = []

    def create_snippet(payload):
        created_snippets.append(payload)
        return {"status": "success", "trigger": payload.get("trigger")}

    adapter = SnippetSenseAdapter(engine=engine, snippet_creator=create_snippet)
    assert adapter.available()

    ok, err = adapter.start({})
    assert ok and err is None

    # simulate a suggestion
    payload = {"hash": "h1", "phrase": "Hello world", "count": 1, "timestamp": "2025-01-01T00:00:00Z"}
    engine.simulate(payload)

    pending = adapter.list_pending()
    assert len(pending) == 1
    sid = pending[0]["id"]

    # accept it
    res = adapter.handle_decision(sid, "accept")
    assert res["status"] == "success"
    # snippet created
    assert len(created_snippets) == 1

    # simulate another suggestion and mark never
    engine.simulate({"hash": "h2", "phrase": "Do not show", "count": 1})
    p2 = adapter.list_pending()
    assert len(p2) == 1
    sid2 = p2[0]["id"]
    res2 = adapter.handle_decision(sid2, "never")
    assert res2["status"] == "success"

    # ensure blocked hash won't be re-added
    engine.simulate({"hash": "h2", "phrase": "Do not show", "count": 2})
    assert all(item.get("hash") != "h2" for item in adapter.list_pending())

    # simulate another suggestion and reject
    engine.simulate({"hash": "h3", "phrase": "Maybe later", "count": 1})
    s3 = adapter.list_pending()
    sid3 = s3[0]["id"]
    res3 = adapter.handle_decision(sid3, "reject")
    assert res3["status"] == "success"
