from core.cli_adapter import CLIAdapter


class BrokenCLI:
    def run(self, args, **kwargs):
        raise RuntimeError("simulated failure")

    def status(self):
        raise RuntimeError("simulated failure")

    def packages(self):
        return []

    def reload(self):
        raise RuntimeError("simulated failure")


def test_cli_adapter_subprocess_fallback():
    adapter = CLIAdapter(cli=BrokenCLI())

    records = []

    def fake_subprocess_run(cmd, *args, **kwargs):
        records.append((cmd, kwargs.get("cwd")))

        class _Result:
            returncode = 0
            stdout = "fallback"
            stderr = ""

        return _Result()

    # Patch subprocess.run directly on the module to avoid pytest fixtures
    import core.cli_adapter as module  # noqa: E402

    saved = module.subprocess.run
    module.subprocess.run = fake_subprocess_run
    try:
        result = adapter.run(["package", "list"])
    finally:
        module.subprocess.run = saved

    assert result.stdout == "fallback"
    assert records
    first_cmd = records[0][0]
    if isinstance(first_cmd, str):
        assert "package" in first_cmd and "list" in first_cmd
    else:
        assert first_cmd[-2:] == ["package", "list"]
