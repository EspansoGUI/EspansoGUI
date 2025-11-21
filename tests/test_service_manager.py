import subprocess

from core.service_manager import ServiceManager


class FakeEspansoCli:
    """Minimal fake CLI that tracks start requests for the service manager tests."""

    def __init__(self) -> None:
        self.started = False
        self.start_requests = 0
        self.status_checks = 0

    def run(self, args, **kwargs):
        cmd = list(args)
        if cmd == ["--version"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="espanso 2.1.0\n", stderr="")
        if cmd == ["status"]:
            self.status_checks += 1
            if self.started:
                return subprocess.CompletedProcess(cmd, 0, stdout="Espanso running\n", stderr="")
            return subprocess.CompletedProcess(cmd, 1, stdout="Espanso not running\n", stderr="service down")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    def start_background(self, args, cwd=None):
        assert list(args) == ["start"]
        self.start_requests += 1
        self.started = True

        class DummyProcess:
            def __init__(self):
                self.pid = 1234

        return DummyProcess()


def test_service_manager_start_once_when_requested():
    fake_cli = FakeEspansoCli()
    manager = ServiceManager(fake_cli, status_delay=0.0)

    first_status = manager.report_service_status(start_if_missing=True)
    assert first_status[0] == "success"
    assert fake_cli.start_requests == 1

    second_status = manager.report_service_status(start_if_missing=True)
    assert second_status[0] == "success"
    assert fake_cli.start_requests == 1


def test_service_manager_returns_warning_without_start():
    fake_cli = FakeEspansoCli()
    manager = ServiceManager(fake_cli, status_delay=0.0)

    status = manager.report_service_status()
    assert status[0] == "warning"
    assert fake_cli.start_requests == 0


"""
CHANGELOG
2025-11-21 Codex
- Added targeted tests for the new `ServiceManager`, covering idempotent starts and non-invasive status checks.
"""
