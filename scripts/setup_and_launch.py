"""Bootstrap script that installs per-OS dependencies then launches EspansoGUI."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request

from pathlib import Path


WEBVIEW2_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


def install_requirements() -> None:
    print("Installing Python requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])


def ensure_webview2() -> None:
    if platform.system() != "Windows":
        return

    possible = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\EdgeWebView\Application\msedgewebview2.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\EdgeWebView\Application\msedgewebview2.exe"),
    ]
    if any(Path(path).exists() for path in possible):
        return

    print("Downloading WebView2 runtime...")
    dest = Path(tempfile.gettempdir()) / "MicrosoftEdgeWebView2RuntimeInstaller.exe"
    urllib.request.urlretrieve(WEBVIEW2_URL, dest)
    print("Running WebView2 runtime installer, please approve any UAC prompts...")
    subprocess.check_call([str(dest)])
    try:
        dest.unlink()
    except Exception:
        pass


def select_backend_env() -> dict[str, str]:
    env = os.environ.copy()
    if platform.system() == "Windows":
        env.setdefault("PYWEBVIEW_GUI", "winforms")
    return env


def main() -> None:
    try:
        install_requirements()
        ensure_webview2()
        env = select_backend_env()
        print("Launching EspansoGUI...")
        subprocess.run([sys.executable, "espansogui.py"], env=env, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] Setup script failed: {exc}", file=sys.stderr)
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
