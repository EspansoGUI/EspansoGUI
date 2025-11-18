# EspansoGUI

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#license)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-informational.svg)](#cross-platform-support)
[![PyWebView](https://img.shields.io/badge/gui-pywebview-green.svg)](https://pywebview.flowrl.com/)

> A PyWebView desktop shell that exposes Espanso's CLI, YAML, and snippet ecosystem through a modern Snippet + Variable IDE with built-in diagnostics, backups, and automation helpers.

EspansoGUI discovers the active Espanso workspace, monitors the daemon, and exposes every major workflow (authoring, backups, diagnostics, packages, and the SnippetSense suggestion engine) through a single window. The backend (`EspansoAPI`) wraps Espanso's CLI, YAML parsing, watcher telemetry, and safety backups so the HTML/JS dashboard can stay fast, offline-friendly, and cross-platform.

---

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
   - [Requirements](#requirements)
   - [Installation](#installation)
   - [Launch](#launch)
3. [Features](#features)
4. [Cross-Platform Support](#cross-platform-support)
5. [Usage Walkthrough](#usage-walkthrough)
6. [SnippetSense](#snippetsense)
7. [Testing & Verification](#testing--verification)
8. [Troubleshooting](#troubleshooting)
9. [Contributing](#contributing)
10. [License](#license)

---

## Overview
- **Backend-first architecture** – `EspansoAPI` exposes 30+ methods (paths, snippets, variables, packages, diagnostics) to the PyWebView JavaScript bridge.
- **Safety-first editing** – Every modification of `base.yml` and related match files is validated, backed up, and replayed to Espanso instantly.
- **Productivity-focused UX** – A Snippet IDE, global variable editor, forms/regex builder, and Quick Insert palette streamline both beginner and power-user workflows.
- **Observability** – Dashboard connection steps, log streaming, doctor diagnostics, match testing, and watcher telemetry keep the daemon healthy.
- **Automation** – SnippetSense monitors repetitive typing locally (respecting privacy) and turns accepted phrases into live Espanso snippets with a single click.

---

## Getting Started

### Requirements
- Python 3.10+
- Espanso 2.3.0+ available on `PATH`
- Node/Web runtime **not** required (PyWebView embeds the HTML/JS bundle)
- Optional: `pynput` + `psutil` for SnippetSense (auto-installed via `requirements.txt`)

### Installation
```bash
pip install -r requirements.txt
```

### Launch
```bash
python espansogui.py
```

> **Tip:** Keep the Espanso daemon running. The dashboard automatically refreshes snippets, config metadata, logs, and diagnostics every few seconds without needing to click "Refresh".

---

## Features

### Core Control
- **Connection Dashboard** – Start/stop/restart Espanso, view CLI output, audit connection steps, and stream log/diagnostic snippets.
- **Path Explorer & Storage Controls** – Detect or override config/match directories, relocate YAML/backup roots, and visualize import trees.
- **Backups** – Timestamped backups on every save plus manual full-config archives and one-click restore.

### Snippet & Variable IDE
- **Authoring** – Trigger + replacement editor with metadata (labels, enable/disable, backend selector, delay, casing, image path) and `$|$` cursor helpers.
- **Search & Bulk** – Advanced filtering (file, enabled state, has vars/forms, label), pagination, and multi-select enable/disable/export.
- **Templates** – Five built-in snippet templates plus drag/drop image preview and a date/shell helper toolkit.
- **Variables** – Modal builder for all Espanso variable types, local insertion buttons, and a read-only global variable browser.

### Forms & Regex
- **Form Builder** – Visual designer for form fields (text, radio, checkbox, select, list) with validation.
- **Regex Tester** – Live validation, capture-group display, and inline testing.

### App-Specific Configs
- Config wizard with filter_exec/filter_title helpers, common templates (VS Code, Chrome, Slack, Terminal, Outlook), and list management.

### CLI & Utilities
- Package manager (list/install/update/uninstall), log viewer, match testing with CLI output, YAML editor with validation, manual backup/restore, and Quick Insert palette for low-friction trigger lookup.

### UI/UX Enhancements
- Keyboard shortcuts (Ctrl/Cmd+K search, Ctrl/Cmd+S save, Ctrl/Cmd+N new snippet, Esc close modal/reset form).
- Light/dark theme toggle with persistence, responsive layout (grids collapse under 1280px), and structured panels that avoid overlapping content.

---

## Cross-Platform Support

| Platform | GUI Runtime | Notes |
|----------|-------------|-------|
| Windows  | Microsoft Edge WebView2 (bundled on modern Windows) | PyWebView prefers the Edge backend; SnippetSense app filtering is Windows-only. |
| macOS    | PyQt5 + PyQtWebEngine | Install via `pip install pyqt5 pyqtwebengine` (or `brew install pyqt@5`). |
| Linux    | PyQt5 + PyQtWebEngine **or** GTK (`python3-gi gir1.2-webkit2-4.0`) | Install distro packages, e.g., `sudo apt install python3-pyqt5 qtwebengine5-dev`. |

If PyWebView cannot initialize a GUI backend, EspansoGUI now cycles through every supported renderer and prints platform-specific recovery steps. Running inside WSL automatically relaunches the Windows copy via `py.exe`/`python.exe`; otherwise enable WSLg or an X11 server.

---

## Usage Walkthrough

### Dashboard & Diagnostics
1. Launch the app – the dashboard auto-loads (no manual refresh needed).
2. Review connection steps: missing CLI, disabled daemon, or watcher issues surface here.
3. Use **Start/Stop/Restart** buttons to control Espanso; log and doctor panels refresh on a schedule.

### YAML Editor
- Use **Save & Reload** to push edits to Espanso; validation prevents malformed YAML from landing.
- Reload from disk at any time or inspect `.espanso_companion/editor_backups/` for timestamped snapshots.

### Snippet IDE Workflow
1. Open **Snippet IDE**.
2. Select an existing snippet or click **New Snippet** (top-right) to clear the form.
3. Adjust metadata (labels, backend, delay, casing, word boundaries, image path) and insert variables/`$|$` markers.
4. Hit **Save Snippet** – the backend backs up, writes, restarts Espanso, refreshes the list, and updates the Quick Insert results.

### Snippet Library & Quick Insert
- Library view: advanced filters, pagination, and bulk enable/disable/export. Quick Insert provides a searchable palette with previews, copy-to-clipboard, and double-click-to-edit.

### Variables & Toolkits
- Global variables tab allows CRUD with type-specific controls; local variables live directly within the Snippet IDE panel.
- Shell/date helpers test commands, preview offsets, and insert templated placeholders (`{{input}}`, `{{clipboard}}`, etc.).

### Paths & Storage
- View auto-detected paths, override config roots, relocate YAML/backups, inspect environment overrides, and render config/import trees.

### Packages, Logs, Backups, Match Testing
- **Packages** – List, refresh, update all, install/uninstall packages.
- **Logs** – Stream CLI output with auto-scroll.
- **Backup/Restore** – Manual snapshot and restore UI with rotation awareness.
- **Match Testing** – Uses `espanso match exec` to show exact outputs or CLI errors in-line.

### SnippetSense Panel
- Enable/disable monitoring, adjust thresholds, maintain allow/block lists, and respond to pending suggestions via toasts or the suggestion queue.

### Help / Playbook
- The in-app **Help** tab hosts scenario cards (First-Time Setup, Build Your First Snippet, Diagnostics, Advanced Authoring) mirroring the “Playbook” summary above.

---

## SnippetSense
- **Privacy-first** – No keystrokes leave the machine; only hashed phrases + counts are stored locally.
- **Cross-platform engine** – Monitoring uses `pynput` on every OS; Windows exposes extra app whitelist/blacklist filters.
- **Idle-aware** – Automatically pauses after 30s of inactivity and resumes monitoring when typing continues.
- **Suggestion pipeline** – Detected phrases enqueue toast prompts inside the GUI; accepting creates a snippet (auto-loading it into the IDE for editing) and restarts Espanso.

---

## Testing & Verification
Run the CLI helpers before submitting changes or tagging a release:

```bash
python verify_fixes.py      # Smoke-test CLI discovery + API wiring
python test_gui_apis.py     # Invoke every JS-exposed API method
python3 -m py_compile espansogui.py snippetsense_engine.py  # Syntax gate
```

Record the test output in `context/test-log.md` per the repository workflow.

---

## Troubleshooting
| Symptom | Fix |
|---------|-----|
| Dashboard stuck on “Connecting…” | Ensure Espanso CLI is installed and accessible. The UI now pings the backend; check terminal logs for CLI errors. |
| GUI fails to open | Install the runtime from the [Cross-Platform Support](#cross-platform-support) table (Edge WebView2 on Windows, PyQt5/WebEngine on macOS/Linux). |
| Snippets save but do not expand | Verify Espanso restarted successfully (toast + dashboard). Use **Match Testing** to inspect the trigger output and review YAML via the editor. |
| SnippetSense errors | Confirm `pynput`/`psutil` are installed. Windows-only app filters require `psutil` and Win32 APIs. |
| Running inside WSL | EspansoGUI relaunches via the Windows interpreter; ensure Windows Python has dependencies or run within WSLg. |
| CLI path mismatch | Use **Paths & Explorer → Move YAML Files** to relocate/migrate directories, or clear overrides to revert to auto-detected paths. |

---

## Contributing
1. Read `AGENTS.md` for the shared workflow (context files, changelog blocks, testing requirements).
2. Create a plan, implement the change, and append a changelog entry to every modified source file.
3. Run the tests listed above and document outputs in `context/test-log.md`.
4. Submit pull requests with a focused scope and include screenshots/gifs for UI changes when possible.

---

## License
MIT. See [LICENSE](LICENSE) for details.
