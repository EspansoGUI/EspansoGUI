from __future__ import annotations

from typing import Sequence, Optional, Any, Dict, List, Tuple
import os
import shutil
import subprocess
import sys
import shlex

try:
    from espanso_companion.cli_integration import EspansoCLI
except Exception:  # pragma: no cover - in tests we inject a fake
    EspansoCLI = None  # type: ignore


class CLIAdapter:
    """Thin adapter around EspansoCLI to create an injectable test seam.

    Methods mirror the small subset of CLI functionality the GUI needs.
    """

    def __init__(self, cli: Optional[Any] = None) -> None:
        # Allow injection of a fake CLI for tests; otherwise construct the real one lazily
        self._cli = cli

    @property
    def cli(self) -> Any:
        if self._cli is None:
            if EspansoCLI is None:
                raise RuntimeError("EspansoCLI is not available in this environment")
            self._cli = EspansoCLI()
        return self._cli

    def run(self, args: Sequence[str], cwd: Optional[str] = None, capture_output: bool = True, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run an espanso CLI command and return CompletedProcess-like object.

        This delegates to `EspansoCLI.run` which returns an object with attributes
        `returncode`, `stdout`, and `stderr`.
        """
        # Prefer the injected/underlying CLI wrapper when available
        try:
            proc = self.cli.run(list(args))
            # Some wrappers may return None or a custom object; normalize
            if proc is None:
                raise RuntimeError("Underlying CLI returned no result")
            return proc
        except Exception:
            cmd = list(args)
            try:
                resolved_cmd, use_shell = self._normalize_command(cmd)
                if use_shell:
                    cmd_str = " ".join(shlex.quote(p) for p in resolved_cmd)
                    completed = subprocess.run(
                        cmd_str,
                        shell=True,
                        capture_output=capture_output,
                        text=True,
                        timeout=timeout,
                        cwd=cwd,
                    )
                else:
                    completed = subprocess.run(
                        resolved_cmd,
                        cwd=cwd,
                        capture_output=capture_output,
                        text=True,
                        timeout=timeout,
                    )
                return completed
            except Exception as exc:
                class _CP:
                    def __init__(self, rc=1, out="", err=""):
                        self.returncode = rc
                        self.stdout = out
                        self.stderr = err

                return _CP(rc=1, out="", err=str(exc))

    def start_background(self, args: Sequence[str], cwd: Optional[str] = None) -> subprocess.Popen:
        """Start a CLI command without waiting for completion."""
        resolved_cmd, use_shell = self._normalize_command(list(args))
        if use_shell:
            cmd_str = " ".join(shlex.quote(p) for p in resolved_cmd)
            return subprocess.Popen(
                cmd_str,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
            )
        return subprocess.Popen(
            resolved_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
        )

    def status(self) -> Dict[str, Any]:
        return self.cli.status()

    def packages(self) -> List[Dict[str, Any]]:
        return self.cli.packages()

    def reload(self) -> subprocess.CompletedProcess:
        return self.cli.reload()

    def set_config_dir(self, path: str) -> None:
        try:
            self.cli.set_config_dir(path)
        except Exception:
            # Surface as no-op for environments where the CLI wrapper is absent
            pass

    def install_installer(self) -> str:
        """Attempt to invoke installer helper on the underlying CLI.

        Not all EspansoCLI implementations expose this; raise when not available.
        Returns path to downloaded installer when implemented.
        """
        cli = self.cli
        install_fn = getattr(cli, "install_installer", None)
        if not install_fn:
            raise NotImplementedError("Underlying CLI does not implement installer helper")
        return install_fn()

    def _normalize_command(self, cmd: List[str]) -> Tuple[List[str], bool]:
        """Ensure fallback command includes a resolved executable and platform-specific shell flag."""
        exe = self._resolve_executable()
        if not cmd:
            cmd_list = [exe]
        else:
            base = os.path.basename(cmd[0])
            if base in {"espanso", "espanso.exe", "espanso.cmd"}:
                cmd_list = [exe] + cmd[1:]
            else:
                cmd_list = cmd[:]
        use_shell = exe.endswith(".cmd") or exe.endswith(".bat")
        return cmd_list, use_shell

    def _resolve_executable(self) -> str:
        """Determine which `espanso` binary to invoke when the wrapper is unavailable."""
        env_override = os.environ.get("ESPANSO_CLI")
        if env_override:
            return env_override
        candidates = ("espanso.exe", "espanso.cmd", "espanso")
        for name in candidates:
            path = shutil.which(name)
            if path:
                return path
        return "espanso"
