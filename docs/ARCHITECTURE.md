# EspansoGUI Architecture Documentation

**Version:** 1.0 Beta
**Last Updated:** 2025-11-21

---

## Overview

EspansoGUI is undergoing a phased refactor from a monolithic architecture to a modular, OOP-based design following SOLID principles.

**Current Status:** ~90% refactored
**Target:** 100% modular by v1.0 release

---

## Architecture Evolution

### Phase 1: Monolithic (Pre-2025)

```
espansogui.py (2000+ LOC)
    └── EspansoAPI class (everything in one file)
```

**Problems:**
- Hard to test
- Tight coupling
- No separation of concerns
- 2000+ lines in single file

---

### Phase 2: Modular (Current)

```
Project Root
├── espansogui.py          — Legacy API (being phased out)
├── ui/
│   └── gui_api.py         — Clean facade for GUI
├── core/                  — Modular backend
│   ├── cli_adapter.py
│   ├── config_manager.py
│   ├── path_manager.py
│   ├── snippet_store.py
│   ├── snippet_service.py
│   ├── backup_manager.py
│   ├── watcher_manager.py
│   └── path_service.py
├── tests/                 — Unit & integration tests
├── webview_ui/            — Frontend HTML/CSS/JS
└── docs/                  — Documentation
```

**Benefits:**
- Testable (17/17 tests passing)
- Loosely coupled
- Clear responsibilities
- ~200 LOC per module

---

## Design Principles

### SOLID Principles Applied

**S - Single Responsibility**
- `CLIAdapter`: Only handles CLI command execution
- `SnippetStore`: Only manages snippet CRUD
- `BackupManager`: Only manages backups

**O - Open/Closed**
- `SnippetStore` extensible via inheritance
- New backends can be added without modifying core

**L - Liskov Substitution**
- All managers implement consistent interfaces
- Can swap implementations without breaking clients

**I - Interface Segregation**
- Small, focused interfaces
- Clients only depend on methods they use

**D - Dependency Inversion**
- High-level modules depend on abstractions
- `PathService` depends on `PathManager` interface, not concrete implementation

---

### DRY (Don't Repeat Yourself)

**Before (Monolithic):**
```python
# Path resolution repeated 5+ times
path = Path.home() / ".config" / "espanso"
if not path.exists():
    path.mkdir(parents=True)
```

**After (Modular):**
```python
from core.path_manager import PathManager
paths = PathManager().get_paths()  # Centralized logic
```

---

## Module Architecture

### Core Modules

#### `core/cli_adapter.py`

**Purpose:** Thin wrapper around Espanso CLI

**Responsibilities:**
- Execute CLI commands
- Handle Windows .cmd vs .exe resolution
- Timeout management
- Background process spawning

**Dependencies:** None (standalone)

**Key Methods:**
- `run(args)` — Synchronous execution
- `start_background(args)` — Async execution
- `status()` — Get espanso status

**Testing:** `tests/test_cli_adapter.py`

---

#### `core/snippet_store.py`

**Purpose:** CRUD operations for snippets

**Responsibilities:**
- Read/write YAML snippet files
- Validate snippet structure
- Handle file-based storage

**Dependencies:**
- `YamlProcessor` for parsing
- `PathManager` for file locations

**Key Methods:**
- `list_snippets()` — Read all
- `create_snippet(snippet)` — Create
- `update_snippet(trigger, snippet)` — Update
- `delete_snippet(trigger)` — Delete

**Testing:** `tests/test_snippet_store_crud.py`

---

#### `core/snippet_service.py`

**Purpose:** Higher-level snippet operations

**Responsibilities:**
- Coordinate snippet operations
- Trigger Espanso reloads
- Business logic layer

**Dependencies:**
- `SnippetStore` for persistence
- `CLIAdapter` for reloads

**Key Methods:**
- `restart()` — Reload Espanso

**Testing:** `tests/test_snippet_service.py`

---

#### `core/backup_manager.py`

**Purpose:** Backup/restore functionality

**Responsibilities:**
- Create timestamped backups
- List available backups
- Restore from backup

**Dependencies:** None

**Key Methods:**
- `create_backup(source, label)`
- `list_backups()`
- `restore_backup(backup_file, target)`

**Testing:** `tests/test_backup_manager.py`

---

#### `core/watcher_manager.py`

**Purpose:** File system monitoring

**Responsibilities:**
- Watch directories for changes
- Emit events on file modifications
- Thread-safe event collection

**Dependencies:**
- `watchdog` library

**Key Methods:**
- `register(path, handler)`
- `poll_events()`
- `stop()`

**Testing:** `tests/test_watcher_manager.py`

---

#### `core/config_manager.py`

**Purpose:** Configuration persistence

**Responsibilities:**
- Read/write GUI preferences
- Validate configuration
- Handle platform differences

**Dependencies:** None

**Testing:** `tests/test_config_manager.py`

---

#### `core/path_manager.py`

**Purpose:** Path discovery and resolution

**Responsibilities:**
- Locate Espanso config directories
- Handle platform-specific paths
- Environment variable resolution

**Dependencies:**
- `CLIAdapter` for `espanso path` command

**Testing:** `tests/test_path_manager.py`

---

### UI Layer

#### `ui/gui_api.py`

**Purpose:** Clean API facade for GUI

**Current Status:** Thin wrapper (delegates to legacy `EspansoAPI`)

**Future:** Will become primary API, directly using `core/` modules

**Benefits:**
- Stable interface for GUI
- Decouples GUI from backend refactor
- Easy to test

---

### Legacy Code

#### `espansogui.py`

**Current Status:** ~2000 LOC, contains `EspansoAPI` class

**Migration Plan:**
1. ✅ Extract core modules (90% complete)
2. ⏸️ Update `GUIApi` to use core modules directly
3. ⏸️ Remove business logic from `EspansoAPI`
4. ⏸️ Keep `EspansoAPI` as compatibility shim

**Remaining Work:**
- Move dashboard logic to `core/dashboard_service.py`
- Move variable logic to `core/variable_manager.py`
- Move SnippetSense to `core/snippetsense_adapter.py`

---

## Frontend Architecture

### Technology Stack

- **PyWebView** — Python-to-HTML bridge
- **Vanilla JavaScript** — No frameworks, simple and fast
- **CSS Variables** — Theming support

### HTML Structure

```
webview_ui/espanso_companion.html (~4100 LOC)
    ├── <style> — CSS (light/dark themes)
    ├── <body> — UI components
    └── <script> — Application logic
```

### Communication Pattern

```
HTML/JavaScript
    ↕ (pywebview.api.*)
Python API (EspansoAPI)
    ↕
Core Modules
    ↕
Espanso CLI
```

**Example:**
```javascript
// Frontend
const dashboard = await window.pywebview.api.get_dashboard();

// Backend
def get_dashboard(self) -> Dict[str, Any]:
    return {
        "snippetCount": len(self.snippet_store.list_snippets()),
        "status": self.cli.status()
    }
```

---

## Data Flow

### Snippet Creation Flow

```
1. User fills form in GUI
2. JavaScript calls window.pywebview.api.create_snippet(snippet)
3. EspansoAPI.create_snippet() validates
4. SnippetStore.create_snippet() writes YAML
5. FileWatcher detects change
6. Cache invalidated
7. GUI refreshes snippet list
```

### Configuration Change Flow

```
1. User edits config
2. ConfigManager validates
3. Writes to JSON file
4. App reads on next launch
```

---

## Caching Strategy

### Performance Optimizations (Session 1)

**Connection State Cache:**
- TTL: 30 seconds
- Prevents repeated CLI calls
- Stored in `_connection_verified` flag

**CLI Status Cache:**
- TTL: 10 seconds
- Reduces `espanso status` spam
- Stored in `_cli_status_cache`

**Snippet List Cache:**
- Invalidated on file changes
- Stored in `_match_cache`
- Populated lazily

**File Watcher Debounce:**
- 2-second delay before reload
- Prevents mid-typing config changes
- Uses `threading.Timer`

---

## Threading Model

### Main Thread
- PyWebView GUI
- User interactions
- API calls

### Background Threads
- File watcher (`WatcherManager`)
- SnippetSense keyboard monitor (if enabled)
- Espanso service start (background process)

### Thread Safety
- Event queue uses `threading.Lock`
- Debounce timer uses `threading.Timer`
- Shared state protected by locks

---

## Error Handling

### Defensive Patterns

**1. Graceful Degradation**
```python
def get_dashboard(self):
    try:
        snippets = self.snippet_store.list_snippets()
    except Exception:
        snippets = []  # Continue with empty list
    return {"snippetCount": len(snippets)}
```

**2. User-Friendly Messages**
```python
if result["status"] == "error":
    return {"status": "error", "detail": "Friendly message for user"}
```

**3. Logging Without Crashing**
```python
try:
    watcher.stop()
except Exception as exc:
    print(f"Warning: {exc}", flush=True)
    # Continue shutdown
```

---

## Testing Strategy

### Test Coverage

```
tests/
├── test_backup_manager.py       — Backup CRUD
├── test_cli_adapter.py          — CLI execution
├── test_cli_adapter_executable  — Windows exe resolution
├── test_cli_adapter_fallback    — Fallback logic
├── test_compat_api.py           — Legacy API compatibility
├── test_config_manager.py       — Config persistence
├── test_gui_smoke.py            — GUI initialization
├── test_path_manager.py         — Path discovery
├── test_snippet_service.py      — Snippet operations
├── test_snippet_store_crud.py   — CRUD operations
├── test_snippet_store_pack.py   — Import/export
├── test_snippet_store_read.py   — Read operations
├── test_snippetsense_adapter.py — SnippetSense logic
└── test_watcher_manager.py      — File monitoring
```

**Current Status:** 17/17 passing

### Test Principles

**1. Unit Tests**
- Test one module at a time
- Mock dependencies
- Fast execution (<1s per test)

**2. Integration Tests**
- Test module interactions
- Use real filesystem (temp directories)
- Clean up after execution

**3. Smoke Tests**
- Quick sanity checks
- Run before commits
- Verify basic functionality

---

## Performance Characteristics

### Startup Time
- **Target:** <2 seconds
- **Current:** ~1.5 seconds
- **Bottleneck:** PyWebView initialization

### Memory Usage
- **Target:** <200MB
- **Current:** ~150MB
- **Growth:** +1MB per 100 snippets

### Snippet Expansion Speed
- **Espanso controlled** — GUI doesn't affect expansion
- **Reload time:** ~500ms (Espanso restart)

---

## Security Considerations

### Input Validation
- All user input validated before writing YAML
- Regex patterns tested before saving
- Shell commands have timeout limits

### File System Safety
- Backups before destructive operations
- Atomic writes (write to temp, then rename)
- Permission checks before operations

### Process Isolation
- CLI commands run in separate processes
- Timeouts prevent hanging
- No shell=True except where necessary

---

## Cross-Platform Support

### Platform Detection

```python
from core.platform_info import PLATFORM

if PLATFORM.system == "win32":
    # Windows-specific code
elif PLATFORM.system == "darwin":
    # macOS-specific code
else:
    # Linux-specific code
```

### Path Handling

```python
from pathlib import Path  # Cross-platform paths

config_dir = Path.home() / ".config" / "espanso"  # Works everywhere
```

### CLI Differences

```python
# Windows: espanso.cmd vs espanso.exe
# Linux/Mac: espanso

cli_adapter = CLIAdapter()  # Handles platform differences automatically
```

---

## Future Architecture Plans

### Phase 3: Complete Modularization (v1.0)

**Remaining Work:**
1. Extract `DashboardService` from `EspansoAPI`
2. Extract `VariableManager` from `EspansoAPI`
3. Extract `SnippetSenseAdapter` (already exists, but not fully integrated)
4. Reduce `espansogui.py` to <500 LOC (just `main()` and `EspansoAPI` shim)

### Phase 4: Plugin System (v2.0)

**Goals:**
- Third-party variable types
- Custom backends
- Extension API

**Design:**
```python
from core.plugin_manager import PluginManager

plugins = PluginManager()
plugins.register("my-variable-type", MyVariableType)
```

### Phase 5: Event-Driven Architecture (v3.0)

**Goals:**
- Async operations
- Real-time updates
- WebSocket communication

**Design:**
```python
from core.event_bus import EventBus

bus = EventBus()
bus.subscribe("snippet.created", on_snippet_created)
bus.publish("snippet.created", snippet)
```

---

## Development Guidelines

### Adding New Modules

1. Create in `core/` directory
2. Follow single responsibility principle
3. Write tests first (TDD)
4. Update `__init__.py` imports
5. Document in API_REFERENCE.md

### Code Style

```python
# Use type hints
def create_snippet(self, snippet: Dict[str, Any]) -> Dict[str, str]:
    pass

# Defensive coding
if not snippet:
    return {"status": "error", "detail": "Snippet required"}

# Clear names
def _start_espanso_service(self):  # Good
def _start_svc(self):              # Bad
```

### Testing Requirements

- All new modules must have tests
- Minimum 80% code coverage
- All tests must pass before merge

---

## Deployment

### Build Process

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python tests/run_tests.py

# Package (future)
pyinstaller espansogui.spec
```

### Distribution

**Current:** Source distribution (Git clone + pip install)

**Future:**
- Windows: `.exe` installer
- macOS: `.dmg` package
- Linux: AppImage, `.deb`, `.rpm`

---

## Maintenance

### Code Health Metrics

```bash
# Test coverage
pytest --cov=core tests/

# Code quality
pylint espansogui.py core/

# Type checking
mypy espansogui.py core/
```

### Performance Monitoring

```bash
# Memory profiling
python -m memory_profiler espansogui.py

# CPU profiling
python -m cProfile -o profile.stats espansogui.py
```

---

## Contributing

See `CONTRIBUTING.md` (when created) for:
- Code review process
- Git workflow
- Issue templates
- Pull request guidelines

---

## References

- **SOLID Principles:** [solid-principles.com](https://solid-principles.com)
- **Clean Architecture:** Robert C. Martin
- **Python Best Practices:** PEP 8, PEP 484

---

**Architecture Version:** 2.0 (Modular)
**Refactor Progress:** 90% complete
**Target:** v1.0 Release (100% modular)
