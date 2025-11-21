from pathlib import Path
from unittest.mock import patch

import webview

from espansogui import _start_webview


class DummyPlatform:
    is_windows = False
    is_wsl = False

    def gui_preferences(self):
        return [None]

    def gui_dependency_hint(self):
        return "GUI hint"


class DummyWindow:
    pass


def test_start_webview_handles_backend_failure():
    calls = []

    def fake_start(*args, **kwargs):
        calls.append((args, kwargs))
        raise webview.errors.WebViewException("no backend")

    window = DummyWindow()
    platform = DummyPlatform()
    script_path = Path(__file__)
    with patch("webview.start", fake_start):
        try:
            _start_webview(window, platform, script_path)
        except webview.errors.WebViewException:
            pass
    assert calls
