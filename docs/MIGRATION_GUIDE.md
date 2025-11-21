# Migration Guide: Vanilla Espanso → EspansoGUI

**Version:** 1.0 Beta
**Last Updated:** 2025-11-21

---

## Overview

This guide helps existing Espanso users adopt EspansoGUI without losing their snippets or configuration.

**Key Point:** EspansoGUI is a **management interface** for Espanso, not a replacement. Your existing snippets continue working exactly as before.

---

## Quick Start (5 Minutes)

### Step 1: Install EspansoGUI

```bash
git clone https://github.com/yourusername/espansogui.git
cd espansogui
pip install -r requirements.txt
```

### Step 2: Launch GUI

```bash
python espansogui.py
```

**EspansoGUI automatically detects your existing Espanso configuration.**

### Step 3: Verify Snippets Loaded

1. Go to **Snippet Library** tab
2. You should see all your existing snippets
3. No import needed — they're already there!

---

## Compatibility

### What Works Out of the Box

✅ **All existing snippets** — Triggers, replacements, variables
✅ **Config files** — `default.yml`, `base.yml`, custom files
✅ **Packages** — Installed packages continue working
✅ **App-specific configs** — Filter rules preserved
✅ **Global variables** — Accessible and editable

### What Requires No Changes

✅ **Typing behavior** — Snippets expand exactly as before
✅ **Espanso service** — Same daemon, same performance
✅ **Clipboard/Inject backends** — Work identically
✅ **Form snippets** — Dialogs appear the same

---

## File Structure

### Before (Vanilla Espanso)

```
~/.config/espanso/
├── config/
│   └── default.yml
└── match/
    ├── base.yml
    ├── personal.yml
    └── work.yml
```

### After (With EspansoGUI)

```
~/.config/espanso/
├── config/
│   └── default.yml        # Unchanged
└── match/
    ├── base.yml           # Editable in GUI
    ├── personal.yml       # Editable in GUI
    └── work.yml           # Editable in GUI

~/.config/espansogui/      # NEW: GUI-specific data
├── preferences.json       # GUI settings
└── backups/              # Automatic backups
    ├── base.yml.20251121...
    └── personal.yml.20251121...
```

**Important:** EspansoGUI doesn't move or modify your Espanso files. It reads/writes them in place.

---

## Feature Mapping

### Command Line → GUI Equivalents

| CLI Command | GUI Location |
|------------|--------------|
| `espanso edit` | Snippet IDE tab |
| `espanso restart` | Settings → Restart Espanso |
| `espanso status` | Dashboard → Service Status |
| `espanso log` | Logs tab |
| `espanso package list` | Packages tab |
| `espanso package install` | Packages → Install |
| `espanso path` | Paths & Explorer tab |

### Editing Workflows

**Before (CLI):**
```bash
vim ~/.config/espanso/match/base.yml
espanso restart
```

**After (GUI):**
1. Open Snippet Library
2. Click snippet to edit
3. Make changes in IDE
4. Click Save
5. Restart Espanso (one button)

---

## Common Migration Scenarios

### Scenario 1: Basic User (10-50 Snippets)

**Your Setup:**
- `base.yml` with simple triggers
- No variables or forms
- Default configuration

**Migration:**
1. Launch GUI
2. All snippets appear automatically
3. Start using GUI for new snippets
4. Continue using CLI for quick edits if preferred

**Benefits:**
- Visual snippet library
- Search/filter capabilities
- Backup on every save
- No typing config paths

---

### Scenario 2: Power User (100+ Snippets)

**Your Setup:**
- Multiple match files
- Extensive global variables
- App-specific configs
- Custom packages

**Migration:**
1. Launch GUI
2. Verify all files detected (Paths & Explorer)
3. Check global variables (Global Variables tab)
4. Review app configs (filter rules preserved)

**Benefits:**
- Pagination (50 snippets per page)
- Advanced search/filters
- Variable editor with type-specific helpers
- Backup management

---

### Scenario 3: Team/Enterprise

**Your Setup:**
- Shared snippet library
- Version control (Git)
- Standardized templates
- Custom workflows

**Migration:**
1. Install EspansoGUI on each machine
2. Point to shared config directory
3. Use Import/Export for snippet packs
4. Continue using Git for version control

**Benefits:**
- Consistent editing interface
- Easy snippet sharing (export packs)
- Validation before commit
- Reduced training time for new users

---

## Backwards Compatibility

### CLI Still Works

You can continue using `espanso` CLI commands alongside the GUI:

```bash
# Create snippet via CLI
echo "  - trigger: ':test'
    replace: 'Test value'" >> ~/.config/espanso/match/base.yml

# Restart via CLI
espanso restart

# GUI detects changes automatically via file watcher
```

### Manual Edits Supported

Edit YAML files directly with your text editor:
- GUI detects changes (2-second debounce)
- Cache refreshes automatically
- No conflicts

---

## Feature Differences

### GUI Advantages

**✅ Visual Interface**
- See all snippets at once
- Search and filter
- Preview replacements

**✅ Validation**
- YAML syntax checked before saving
- Regex patterns tested
- Shell commands previewed

**✅ Backups**
- Automatic on every save
- Restore from backup
- Timestamped versions

**✅ Advanced Editors**
- Form builder (visual)
- Variable editor (type-specific)
- Regex tester (live preview)

### CLI Advantages

**✅ Speed**
- No GUI startup time
- Direct file access
- Scriptable

**✅ Simplicity**
- No dependencies
- Works over SSH
- Minimal overhead

**✅ Automation**
- Shell scripts
- CI/CD integration
- Programmatic access

---

## Special Cases

### Case 1: Non-Standard Config Location

If you moved your Espanso config:

```bash
export ESPANSO_CONFIG_DIR="/custom/path"
espanso path  # Verify
```

**In GUI:**
1. Go to **Paths & Explorer**
2. Click **"Set Config Override"**
3. Enter `/custom/path`
4. Restart GUI

---

### Case 2: Multiple Profiles

If you use espanso profiles (experimental):

**Current:** GUI doesn't support profile switching yet

**Workaround:**
- Use CLI for profile switching: `espanso env-path set PROFILE_NAME`
- Restart GUI to load new profile

**Future:** Profile selector in GUI (planned for v1.1)

---

### Case 3: Custom Scripts

If you have shell scripts that edit configs:

**Before:**
```bash
#!/bin/bash
echo "  - trigger: ':auto'
    replace: 'Generated'" >> ~/.config/espanso/match/base.yml
espanso restart
```

**After (with GUI running):**
1. Script runs
2. GUI detects file change (2s debounce)
3. Cache refreshes automatically
4. Optional: Call GUI API from script

---

## Troubleshooting Migration

### Issue: Snippets Not Appearing

**Check:**
1. Dashboard → Connection Steps
2. Verify config path matches espanso path
3. Check YAML syntax (might have errors that CLI ignores)

**Fix:**
```bash
# Verify paths match
espanso path
# GUI should show same paths in Paths & Explorer
```

---

### Issue: Duplicate Snippets

**Cause:** Snippet exists in multiple files

**Fix:**
1. Snippet Library → Search for trigger
2. Note which files contain it
3. Delete from one file
4. Keep the version you want

---

### Issue: Performance Degradation

**Cause:** Large snippet library (1000+ snippets)

**Fix:**
1. Split across multiple files
2. Use pagination (already enabled)
3. Disable file watcher if not editing

---

### Issue: Backups Taking Space

**Location:** `~/.config/espansogui/backups/`

**Fix:**
```bash
# List backups
ls -lh ~/.config/espansogui/backups/

# Delete old backups (keep last 30 days)
find ~/.config/espansogui/backups/ -type f -mtime +30 -delete
```

---

## Best Practices

### Hybrid Workflow (Recommended)

**Use GUI for:**
- Creating complex snippets (forms, variables)
- Organizing and searching
- Bulk operations
- Learning Espanso features

**Use CLI for:**
- Quick one-liner additions
- Automated scripts
- Remote management (SSH)
- CI/CD pipelines

---

### Backup Strategy

**Before GUI:**
```bash
cp -r ~/.config/espanso ~/espanso_backup_$(date +%Y%m%d)
```

**With GUI:**
- Automatic backups on every save
- Manual backup: Settings → Backup & Restore
- Export snippet packs for version control

---

### Team Collaboration

**Git + GUI Workflow:**

1. **Setup:**
   ```bash
   cd ~/.config/espanso
   git init
   git add match/
   git commit -m "Initial snippets"
   ```

2. **Edit with GUI:**
   - Make changes in GUI
   - GUI saves to match files
   - Files auto-backed up

3. **Commit:**
   ```bash
   cd ~/.config/espanso
   git add match/
   git commit -m "Added email snippets"
   git push
   ```

4. **Team pulls:**
   ```bash
   git pull
   # GUI detects changes, refreshes automatically
   ```

---

## FAQ

### Does EspansoGUI replace Espanso?

**No.** EspansoGUI is a management interface. Espanso still handles the actual text expansion. You need both.

---

### Can I uninstall EspansoGUI?

**Yes.** Your snippets remain in `~/.config/espanso/`. Just delete the EspansoGUI folder and `~/.config/espansogui/` (GUI settings).

---

### Will my snippets stop working if I close the GUI?

**No.** Espanso runs independently. The GUI is only for management.

---

### Can I use both CLI and GUI?

**Yes.** They work together seamlessly. Edit with either, changes are detected.

---

### Do I need to import my snippets?

**No.** GUI automatically reads from your existing Espanso config directory.

---

### What if I don't like the GUI?

Continue using the CLI exclusively. The GUI is optional.

---

## Migration Checklist

**Before Migration:**
- [ ] Backup Espanso config: `cp -r ~/.config/espanso ~/espanso_backup`
- [ ] Note espanso version: `espanso --version`
- [ ] Test snippets work: Type a few triggers
- [ ] List packages: `espanso package list`

**During Installation:**
- [ ] Install Python 3.8+
- [ ] Clone EspansoGUI repo
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run tests: `python tests/run_tests.py`

**After Installation:**
- [ ] Launch GUI: `python espansogui.py`
- [ ] Verify snippet count matches
- [ ] Test editing a snippet
- [ ] Restart Espanso from GUI
- [ ] Verify triggers still work

**First Week:**
- [ ] Try creating snippet in GUI
- [ ] Try searching/filtering
- [ ] Explore variable editor
- [ ] Create a backup manually
- [ ] Read USER_GUIDE.md

---

## Rollback Plan

If you need to revert:

1. **Close GUI**
2. **Restore backup:**
   ```bash
   rm -rf ~/.config/espanso
   cp -r ~/espanso_backup ~/.config/espanso
   ```
3. **Restart Espanso:**
   ```bash
   espanso restart
   ```
4. **Test snippets**

Your Espanso setup is now exactly as it was before.

---

## Next Steps

1. **Read USER_GUIDE.md** for feature tour
2. **Try Quick Insert** for fast trigger access
3. **Enable SnippetSense** for AI suggestions
4. **Create snippet pack** to share with team
5. **Join community** for tips and support

---

## Support

- **Troubleshooting:** See `TROUBLESHOOTING.md`
- **API Docs:** See `API_REFERENCE.md`
- **Architecture:** See `ARCHITECTURE.md`
- **Issues:** GitHub repository

---

**Welcome to EspansoGUI!** Your snippets, supercharged. 🚀
