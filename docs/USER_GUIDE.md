# EspansoGUI User Guide

**Version:** 1.0 Beta
**Last Updated:** 2025-11-21

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Feature Tour](#feature-tour)
4. [Common Tasks](#common-tasks)
5. [Keyboard Shortcuts](#keyboard-shortcuts)
6. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- **Python 3.8+** installed
- **Espanso** installed and configured ([espanso.org](https://espanso.org))
- **Windows, macOS, or Linux** operating system

### Install Steps

1. **Clone or download** the EspansoGUI repository:
   ```bash
   git clone https://github.com/yourusername/espansogui.git
   cd espansogui
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the GUI:**
   ```bash
   python espansogui.py
   ```

4. **First launch** may take a few seconds while PyWebView initializes.

---

## Quick Start

### Creating Your First Snippet

1. Launch EspansoGUI: `python espansogui.py`
2. Click **"New Snippet"** (or press `Ctrl+N`)
3. Enter a **trigger** (e.g., `:email`)
4. Enter a **replacement** (e.g., `user@example.com`)
5. Click **"Save"** (or press `Ctrl+S`)
6. Type `:email` in any application → Espanso expands it!

### Searching Snippets

1. Press `Ctrl+K` to focus the search box
2. Type keywords to filter snippets
3. Click a snippet card to edit it

### Restarting Espanso

After creating or editing snippets:
1. Go to **Settings** tab
2. Click **"Restart Espanso"**
3. Your changes are now active

---

## Feature Tour

### Dashboard

The **Dashboard** shows at-a-glance status:
- **Service Status:** Is Espanso running?
- **Snippet Count:** How many snippets you have
- **Recent Events:** File changes, config updates
- **Connection Steps:** Diagnostic information

### Snippet Library

Browse and manage all your snippets:
- **Search/Filter:** Find snippets by trigger, label, or content
- **Pagination:** 50 snippets per page for large libraries
- **Quick Actions:** Edit, delete, or duplicate snippets
- **Filters:**
  - By file (base.yml, custom files)
  - By status (enabled/disabled)
  - By type (has variables, has forms)

### Snippet IDE

The **Snippet IDE** is where you create and edit snippets:

#### Basic Fields
- **Trigger:** The text that triggers expansion (e.g., `:sig`)
- **Replacement:** The text to insert
- **Label:** Optional description for organization

#### Advanced Metadata
- **Backend:** `Inject` (fast) or `Clipboard` (compatible)
- **Delay:** Milliseconds to wait before expansion
- **Word Boundaries:** Left/right word boundary detection
- **Uppercase Style:** `Capitalize`, `Uppercase`, or `Lowercase`
- **Image Path:** Insert images on expansion

#### Variables
Add dynamic content to snippets:
- **Echo:** Simple text placeholder
- **Shell:** Run command and insert output
- **Clipboard:** Insert clipboard contents
- **Date:** Insert formatted dates
- **Choice:** Select from dropdown
- **Random:** Random selection from list
- **Form:** Multi-field input dialog

**Example with variables:**
```yaml
Trigger: :meeting
Replace: Meeting at {{time}} with {{person}}
Variables:
  - time: (form field)
  - person: (form field)
```

#### Forms

Create multi-field input dialogs:
1. Click **"Add Form Field"**
2. Choose field type: `text`, `choice`, `list`, `checkbox`, `radio`, `select`
3. Configure options (for choice/list fields)
4. Variables are auto-inserted as `{{field_name}}`

### Global Variables

Reusable variables across all snippets:
- **View:** See all global variables
- **Edit:** Modify existing globals
- **Create:** Add new globals
- **Promote:** Convert local variable to global

### Quick Insert

Fast snippet trigger copying:
1. Open **Quick Insert** view
2. Search for a snippet
3. Click to copy trigger to clipboard
4. Paste trigger in any app

### SnippetSense

Automatic snippet suggestion based on typing patterns:
- **Enable:** Settings → SnippetSense → Toggle On
- **Configure:**
  - Minimum words (default: 3)
  - Repetition threshold (default: 3 times)
  - App whitelist/blacklist (Windows only)
- **Use:**
  - Type repeated phrases naturally
  - SnippetSense suggests converting to snippet
  - Accept, reject, or never suggest again

### App-Specific Configs

Create snippets that only work in specific apps:
1. Go to **Paths & Explorer**
2. Click **"Create App Config"**
3. Choose template (VSCode, Chrome, Slack, etc.)
4. Configure filters:
   - `filter_exec`: Executable name (e.g., `code.exe`)
   - `filter_title`: Window title pattern

### Backup & Restore

Automatic backups on every save:
- **View Backups:** Settings → Backup & Restore
- **Restore:** Select backup, click "Restore"
- **Location:** `~/.config/espansogui/backups/` (Linux/Mac) or `%APPDATA%\espansogui\backups\` (Windows)

---

## Common Tasks

### Import Snippets from JSON/YAML

1. Go to **Snippet Library**
2. Click **"Import Pack"**
3. Select your `.json` or `.yaml` file
4. Review imported snippets
5. Click **"Save"** to confirm

### Export Snippet Pack

1. Select snippets in library (checkboxes)
2. Click **"Export Selected"**
3. Choose export format (JSON or YAML)
4. Save file to share with others

### Disable/Enable Snippets

1. Open snippet in IDE
2. Toggle **"Enabled"** checkbox
3. Save snippet
4. Restart Espanso

### Organize with Labels

1. Edit snippet
2. Add **Label** (e.g., "Work", "Personal", "Code")
3. Filter library by label

### Test Shell Commands

Before saving shell variable:
1. Enter command in shell variable editor
2. Click **"Test Command"**
3. View output/errors
4. Adjust command as needed

### Preview Date Offsets

1. Create date variable
2. Click **"Date Calculator"**
3. Choose offset ("+7 days", "-1 week")
4. Preview shows calculated date

### Check Logs

If snippets aren't expanding:
1. Go to **Logs** tab
2. Review Espanso output
3. Look for errors or warnings
4. Check **Diagnostics** for health issues

---

## Keyboard Shortcuts

### Global
- `Ctrl+K` — Focus search box
- `Ctrl+N` — New snippet
- `Ctrl+S` — Save snippet
- `Esc` — Close modals, clear search

### Navigation
- `Tab` — Navigate between fields
- `Shift+Tab` — Navigate backwards
- `Enter` — Submit forms
- `Esc` — Cancel/close

### Editing
- Standard text editing shortcuts apply
- Undo/Redo work in all text fields

---

## Troubleshooting

### Snippets Not Expanding

**Check:**
1. Is Espanso running? (Dashboard shows status)
2. Did you restart Espanso after changes?
3. Is snippet enabled?
4. Check trigger doesn't conflict with another snippet

**Fix:**
- Go to Settings → Click "Restart Espanso"
- Check Logs for errors
- Run Diagnostics (Doctor tab)

### GUI Won't Launch

**Error:** `No GUI backend available`

**Fix (Windows):**
```bash
pip install pywebview[cef]
```

**Fix (Linux):**
```bash
sudo apt-get install python3-gi python3-gi-cairo gir1.2-webkit2-4.0
pip install pywebview[gtk]
```

**Fix (macOS):**
```bash
pip install pyobjc
```

### Death Loop (Infinite Terminal Scrolling)

**Symptom:** Terminal shows repeated `[ERROR] espanso is not running`

**Fix:**
1. Manually start Espanso: `espanso start`
2. Restart EspansoGUI
3. Check Espanso installed correctly: `espanso --version`

### Triggers Intermittent

**Possible causes:**
- SnippetSense keyboard hooks interfering
- File watcher reloading config mid-typing
- Other text expansion tools running

**Fix:**
- Disable SnippetSense temporarily (Settings)
- Close other text expansion tools
- Check Logs for reload events

### High Memory Usage

**If GUI uses >500MB:**
- Large snippet library (1000+ snippets)
- Circular dependencies in variables
- Watcher monitoring too many files

**Fix:**
- Split snippets across multiple files
- Use pagination (already enabled)
- Restart GUI periodically

---

## Advanced Tips

### Variable Injection Syntax

Use variables in replacement text:
```
Hello {{name}}, today is {{date}}
```

### Nested Variables

Variables can reference other variables:
```yaml
- name: greeting
  type: echo
  params:
    echo: "Hello"

- name: full_greeting
  type: echo
  params:
    echo: "{{greeting}}, how are you?"
```

### Regex Triggers

For pattern-based matching:
```yaml
trigger: ":calc(\\d+)\\+(\\d+)"
replace: "{{result}}"
# Captures numbers and calculates
```

### Cursor Position

Use `$|$` to position cursor:
```yaml
trigger: ":func"
replace: "function $|$() {\n\n}"
```

---

## Getting Help

- **Documentation:** Check other docs in `/docs/` folder
- **Troubleshooting:** See `TROUBLESHOOTING.md`
- **API Reference:** See `API_REFERENCE.md` for developers
- **GitHub Issues:** Report bugs at repository issues page

---

## Next Steps

- **Explore Templates:** Use built-in snippet templates
- **Try SnippetSense:** Let AI suggest snippets from your typing
- **Create Forms:** Build multi-field input dialogs
- **Share Packs:** Export and share snippet collections

---

**Happy Expanding!** 🚀
