# EspansoGUI API Reference

**Version:** 1.0 Beta
**Last Updated:** 2025-11-21

---

## Overview

EspansoGUI exposes a Python API through the `EspansoAPI` class for programmatic access to snippet management, configuration, and Espanso CLI integration.

### Architecture

```
espansogui.py (Legacy Monolith)
    ├── EspansoAPI (Main API, being refactored)
    └── GUIApi (Facade in ui/gui_api.py)

core/ (Modern Modular Backend)
    ├── cli_adapter.py      — CLI command execution
    ├── config_manager.py   — Configuration management
    ├── path_manager.py     — Path discovery
    ├── snippet_store.py    — Snippet CRUD operations
    ├── snippet_service.py  — Higher-level snippet logic
    ├── backup_manager.py   — Backup/restore
    ├── watcher_manager.py  — File system monitoring
    └── path_service.py     — Path initialization

ui/
    └── gui_api.py          — Clean API facade
```

---

## Core Modules

### `core.cli_adapter.CLIAdapter`

Thin wrapper around Espanso CLI commands.

#### Methods

```python
def run(args: Sequence[str], cwd: Optional[str] = None,
        capture_output: bool = True, timeout: int = 30) -> subprocess.CompletedProcess
```
Execute espanso CLI command synchronously.

**Parameters:**
- `args`: Command arguments (e.g., `["status"]`)
- `cwd`: Working directory
- `capture_output`: Capture stdout/stderr
- `timeout`: Timeout in seconds

**Returns:** `CompletedProcess` with `returncode`, `stdout`, `stderr`

**Example:**
```python
from core.cli_adapter import CLIAdapter

cli = CLIAdapter()
result = cli.run(["status"])
if result.returncode == 0:
    print("Espanso is running")
```

---

```python
def start_background(args: Sequence[str], cwd: Optional[str] = None) -> subprocess.Popen
```
Start CLI command without waiting.

**Use case:** Starting espanso daemon

---

```python
def status() -> Dict[str, Any]
```
Get espanso status.

**Returns:**
```python
{
    "returncode": 0,
    "stdout": "espanso is running",
    "stderr": ""
}
```

---

```python
def packages() -> List[Dict[str, Any]]
```
List installed packages.

**Returns:** List of package dicts with `name`, `version`, `author`

---

```python
def reload() -> subprocess.CompletedProcess
```
Restart espanso service.

---

### `core.snippet_store.SnippetStore`

CRUD operations for snippets.

#### Constructor

```python
SnippetStore(match_dir: Path)
```

**Parameters:**
- `match_dir`: Path to `match/` directory

---

#### Methods

```python
def list_snippets() -> List[Dict[str, Any]]
```
List all snippets from all YAML files.

**Returns:** List of snippet dicts

---

```python
def create_snippet(snippet: Dict[str, Any]) -> Dict[str, str]
```
Create new snippet.

**Parameters:**
```python
snippet = {
    "trigger": ":hello",
    "replace": "Hello, world!",
    "label": "Greeting",
    "enabled": True
}
```

**Returns:**
```python
{"status": "success", "detail": "Snippet created"}
```

---

```python
def update_snippet(old_trigger: str, new_snippet: Dict[str, Any]) -> Dict[str, str]
```
Update existing snippet.

---

```python
def delete_snippet(trigger: str) -> Dict[str, str]
```
Delete snippet by trigger.

---

### `core.snippet_service.SnippetService`

Higher-level snippet operations.

```python
def restart() -> Dict[str, str]
```
Reload espanso after snippet changes.

---

### `core.backup_manager.BackupManager`

Manage snippet backups.

```python
def create_backup(source: Path, label: str = "") -> Path
```
Create timestamped backup.

**Returns:** Path to backup file

---

```python
def list_backups() -> List[Dict[str, Any]]
```
List available backups with metadata.

---

```python
def restore_backup(backup_file: Path, target: Path) -> None
```
Restore backup to target location.

---

### `core.watcher_manager.WatcherManager`

File system monitoring.

```python
def register(path: Path, handler: Callable) -> None
```
Watch directory for changes.

---

```python
def poll_events() -> List[Dict[str, Any]]
```
Get recent file events.

---

## Main API (`EspansoAPI`)

### Initialization

```python
from espansogui import EspansoAPI

api = EspansoAPI()
# Automatically initializes paths, watcher, services
```

---

### Dashboard & Status

```python
def get_dashboard() -> Dict[str, Any]
```
Get dashboard data.

**Returns:**
```python
{
    "configPath": "/path/to/config",
    "statusMessage": "Connected",
    "cliStatus": "espanso is running",
    "snippetCount": 42,
    "matchFileCount": 3,
    "formSnippets": 5,
    "variableSnippets": 12,
    "eventCount": 10,
    "recentEvents": [...],
    "connectionSteps": [...]
}
```

---

```python
def ping() -> Dict[str, Any]
```
Lightweight readiness probe.

**Returns:**
```python
{
    "status": "ok",
    "ready": True,
    "snippetCount": 42,
    "configPath": "/path/to/config",
    "platform": "win32"
}
```

---

### Snippet Management

```python
def list_snippets() -> List[Dict[str, Any]]
```
List all snippets (cached).

---

```python
def search_snippets(query: str = "", filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]
```
Search snippets with filters.

**Parameters:**
```python
filters = {
    "file": "base.yml",        # Filter by file
    "enabled": "enabled",      # "enabled" or "disabled"
    "hasVars": True,          # Has variables
    "hasForm": True,          # Has form fields
    "label": "work"           # Label contains text
}
```

**Returns:**
```python
{
    "status": "success",
    "results": [...],
    "count": 10,
    "total": 42
}
```

---

```python
def create_snippet(snippet: Dict[str, Any]) -> Dict[str, str]
```
Create snippet.

**Example:**
```python
snippet = {
    "trigger": ":sig",
    "replace": "Best regards,\nJohn Doe",
    "label": "Email",
    "backend": "inject",
    "delay": 100,
    "left_word": True,
    "right_word": True,
    "uppercase_style": "none"
}
result = api.create_snippet(snippet)
```

---

```python
def update_snippet(trigger: str, snippet: Dict[str, Any]) -> Dict[str, str]
```
Update existing snippet.

---

```python
def delete_snippet(trigger: str) -> Dict[str, str]
```
Delete snippet.

---

### Variable Management

```python
def get_global_variables() -> Dict[str, Any]
```
Get all global variables.

**Returns:**
```python
{
    "status": "success",
    "variables": [
        {
            "name": "myvar",
            "type": "shell",
            "params": {"cmd": "date"}
        }
    ]
}
```

---

```python
def update_global_variables(variables: List[Dict[str, Any]]) -> Dict[str, str]
```
Update global variables.

---

### Form Snippets

```python
def create_form_snippet(trigger: str, form_fields: List[Dict]) -> Dict[str, str]
```
Create snippet with form.

**Example:**
```python
form_fields = [
    {"name": "name", "type": "text", "default": ""},
    {"name": "role", "type": "choice", "values": ["Developer", "Designer", "Manager"]},
    {"name": "agree", "type": "checkbox", "default": True}
]
api.create_form_snippet(":signup", form_fields)
```

---

### Validation & Testing

```python
def validate_regex(pattern: str) -> Dict[str, Any]
```
Validate regex pattern.

---

```python
def test_regex(pattern: str, test_text: str) -> Dict[str, Any]
```
Test regex against text.

**Returns:**
```python
{
    "status": "success",
    "matched": True,
    "match_text": "example@test.com",
    "groups": ["example", "test.com"],
    "span": [0, 17]
}
```

---

```python
def test_shell_command(command: str, timeout: int = 5, use_shell: bool = True) -> Dict[str, Any]
```
Test shell command safely.

---

```python
def preview_date_offset(fmt: str, expression: str) -> Dict[str, Any]
```
Preview date with offset.

**Example:**
```python
api.preview_date_offset("%Y-%m-%d", "+7 days")
# Returns: {"status": "success", "preview": "2025-11-28", "seconds": 604800}
```

---

### Configuration

```python
def get_base_yaml() -> Dict[str, Any]
```
Read base.yml for editing.

---

```python
def save_base_yaml(content: str) -> Dict[str, str]
```
Save base.yml after validation.

---

```python
def get_path_settings() -> Dict[str, Any]
```
Get path configuration.

---

```python
def set_config_override(new_path: str) -> Dict[str, Any]
```
Override config directory.

---

### Service Control

```python
def start_service() -> Dict[str, str]
```
Start espanso daemon.

---

```python
def stop_service() -> Dict[str, str]
```
Stop espanso daemon.

---

```python
def restart_service() -> Dict[str, str]
```
Restart espanso.

---

### Logs & Diagnostics

```python
def get_logs(lines: int = 200) -> Dict[str, Any]
```
Get espanso logs.

---

```python
def get_doctor_output() -> Dict[str, Any]
```
Run espanso doctor diagnostics.

---

### Package Management

```python
def list_packages() -> List[Dict[str, Any]]
```
List installed packages.

---

```python
def install_package(name: str) -> Dict[str, str]
```
Install package from Hub.

---

```python
def uninstall_package(name: str) -> Dict[str, str]
```
Uninstall package.

---

### Backup & Restore

```python
def list_backups() -> Dict[str, Any]
```
List available backups.

---

```python
def create_backup(label: str = "") -> Dict[str, str]
```
Create manual backup.

---

```python
def restore_backup(backup_id: str) -> Dict[str, str]
```
Restore from backup.

---

### Import/Export

```python
def import_snippet_pack(file_path: str) -> Dict[str, Any]
```
Import snippets from JSON/YAML.

---

```python
def export_snippet_pack(triggers: List[str], format: str = "yaml") -> Dict[str, str]
```
Export snippets.

**Parameters:**
- `triggers`: List of snippet triggers to export
- `format`: "yaml" or "json"

---

## Usage Examples

### Complete Workflow

```python
from espansogui import EspansoAPI

# Initialize
api = EspansoAPI()

# Check status
dashboard = api.get_dashboard()
print(f"Snippets: {dashboard['snippetCount']}")

# Create snippet
snippet = {
    "trigger": ":email",
    "replace": "user@example.com",
    "label": "Contact"
}
api.create_snippet(snippet)

# Restart espanso
api.restart_service()

# Search snippets
results = api.search_snippets("email", {"label": "contact"})
print(f"Found {results['count']} snippets")

# Backup
api.create_backup("Before major changes")
```

---

### Error Handling

All API methods return dicts with `status` field:

```python
result = api.create_snippet(snippet)
if result["status"] == "error":
    print(f"Error: {result['detail']}")
else:
    print("Success!")
```

---

### Threading & Performance

**Caching:**
- Connection checks cached for 30s
- CLI status cached for 10s
- Snippet list cached until refresh

**Thread Safety:**
- File watcher runs in background thread
- Event capture uses locks
- SnippetSense engine runs daemon threads

---

## Deprecation Warnings

**Legacy API (espansogui.py):**
The monolithic `EspansoAPI` is being refactored into `core/` modules. Use `core.*` imports for new code:

```python
# Old (still works, but legacy)
from espansogui import EspansoAPI

# New (preferred)
from ui.gui_api import GUIApi
from core.snippet_store import SnippetStore
from core.cli_adapter import CLIAdapter
```

---

## Testing

```python
# Run test suite
python tests/run_tests.py

# Smoke test
python smoke_check.py

# Specific module test
python -m pytest tests/test_snippet_store.py
```

---

## Contributing

See `ARCHITECTURE.md` for design patterns and coding guidelines.

---

**API Version:** 1.0 Beta
**Stability:** Beta (expect minor breaking changes before 1.0)
