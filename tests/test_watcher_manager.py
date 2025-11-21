from core.watcher_manager import WatcherManager
from espanso_companion.file_watcher import WatchEvent
from pathlib import Path


class FakeWatcher:
    def __init__(self):
        self._callbacks = []
        self._events = []

    def start(self):
        pass

    def stop(self):
        pass

    def register_callback(self, cb):
        self._callbacks.append(cb)

    def poll(self):
        evs = list(self._events)
        self._events = []
        return evs

    # test seam
    def simulate_event(self, event: WatchEvent):
        for cb in self._callbacks:
            cb(event)
        self._events.append(event)


import tempfile


def test_watcher_manager_registration_and_poll():
    with tempfile.TemporaryDirectory() as td:
        fw = FakeWatcher()
        wm = WatcherManager(paths=[Path(td)], watcher=fw)
        called = []

        def cb(ev: WatchEvent):
            called.append(ev)

        wm.register_callback(cb)
        wm.start()
        # simulate an event
        ev = WatchEvent(src_path=Path("/tmp/x"), event_type="modified", is_directory=False)
        fw.simulate_event(ev)

        # poll events
        events = wm.poll_events()
        assert len(events) == 1
        assert events[0].event_type == "modified"
        # callback was called
        assert len(called) == 1
        wm.stop()
