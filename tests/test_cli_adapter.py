from core.cli_adapter import CLIAdapter


class DummyCLI:
    def __init__(self):
        self._cfg = None

    def run(self, args):
        import subprocess

        return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")

    def status(self):
        return {"stdout": "ok"}

    def packages(self):
        return []

    def reload(self):
        import subprocess

        return subprocess.CompletedProcess([], 0, stdout="reloaded", stderr="")

    def set_config_dir(self, path):
        self._cfg = path


def test_run_and_status():
    dummy = DummyCLI()
    adapter = CLIAdapter(cli=dummy)
    res = adapter.run(["--version"])
    assert res.returncode == 0
    assert adapter.status()["stdout"] == "ok"
    adapter.set_config_dir("x")
    assert getattr(dummy, "_cfg") == "x"
