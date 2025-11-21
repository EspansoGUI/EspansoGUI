import os
import shutil

from core.cli_adapter import CLIAdapter


class DummyCLI:
    def run(self, args):
        raise RuntimeError("should not run")

    def status(self):
        raise RuntimeError("should not run")

    def packages(self):
        return []

    def reload(self):
        raise RuntimeError("should not run")


def test_resolve_executable_prefers_env():
    adapter = CLIAdapter(cli=DummyCLI())
    original = os.environ.get("ESPANSO_CLI")
    os.environ["ESPANSO_CLI"] = "/tmp/custom/espanso"
    try:
        assert adapter._resolve_executable() == "/tmp/custom/espanso"
    finally:
        if original is None:
            os.environ.pop("ESPANSO_CLI", None)
        else:
            os.environ["ESPANSO_CLI"] = original


def test_resolve_executable_checks_path():
    adapter = CLIAdapter(cli=DummyCLI())
    os.environ.pop("ESPANSO_CLI", None)

    def fake_which(name):
        if name == "espanso.exe":
            return "/path/to/espanso.exe"
        return None

    original_which = shutil.which
    shutil.which = fake_which
    try:
        assert adapter._resolve_executable().endswith("espanso.exe")
    finally:
        shutil.which = original_which


def test_normalize_command_uses_resolved():
    adapter = CLIAdapter(cli=DummyCLI())
    original = os.environ.get("ESPANSO_CLI")
    os.environ["ESPANSO_CLI"] = "/usr/bin/espanso"
    try:
        cmd, use_shell = adapter._normalize_command(["espanso", "status"])
        assert cmd[0] == "/usr/bin/espanso"
        assert use_shell is False
        os.environ["ESPANSO_CLI"] = "/path/to/espanso.cmd"
        cmd, use_shell = adapter._normalize_command(["espanso", "status"])
        assert use_shell is True
    finally:
        if original is None:
            os.environ.pop("ESPANSO_CLI", None)
        else:
            os.environ["ESPANSO_CLI"] = original


def test_resolve_falls_back_to_default():
    adapter = CLIAdapter(cli=DummyCLI())
    original_env = os.environ.pop("ESPANSO_CLI", None)
    original_which = shutil.which
    shutil.which = lambda name: None
    try:
        assert adapter._resolve_executable() == "espanso"
    finally:
        shutil.which = original_which
        if original_env is not None:
            os.environ["ESPANSO_CLI"] = original_env
