"""Diagnose why `espanso start` may block during EspansoGUI initialization."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from typing import Tuple


def _wsl_to_windows(path: str) -> str:
    if not path.startswith("/mnt/"):
        return path
    parts = path.split("/", 3)
    if len(parts) < 4:
        return path
    drive = parts[2].upper()
    tail = parts[3].replace("/", "\\\\")
    return f"{drive}:\\{tail}"


def find_espanso_command() -> Tuple[str, ...]:
    """Return the executable command for the Espanso CLI."""
    for name in ("espanso", "espanso.exe", "espanso.cmd"):
        path = shutil.which(name)
        if path:
            if path.lower().endswith(".cmd"):
                return ("cmd.exe", "/c", _wsl_to_windows(path), "start")
            return (_wsl_to_windows(path), "start")
    raise RuntimeError("Espanso CLI not found on PATH")


def run_cli_command(timeout: int = 30) -> None:
    cmd = find_espanso_command()
    print(f"[DEBUG] Running: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        print(f"[INFO] Completed in {time.perf_counter():.1f}s (returncode={proc.returncode})")
        if stdout:
            print("[STDOUT]\n" + stdout.strip())
        if stderr:
            print("[STDERR]\n" + stderr.strip())
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        print(f"[WARN] Command timed out after {timeout}s (killed).")
        if stdout:
            print("[STDOUT]\n" + stdout.strip())
        if stderr:
            print("[STDERR]\n" + stderr.strip())
        sys.exit(1)


def main() -> None:
    print("[INFO] Diagnosing Espanso start behavior")
    run_cli_command(timeout=30)


if __name__ == "__main__":
    main()
