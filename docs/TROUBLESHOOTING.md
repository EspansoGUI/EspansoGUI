# EspansoGUI Troubleshooting Guide

**Version:** 1.0 Beta
**Last Updated:** 2025-11-21

---

## Quick Diagnostics

**Before troubleshooting, run:**

```bash
# Check Espanso CLI
espanso --version
espanso status

# Check EspansoGUI
python smoke_check.py

# Run tests
python tests/run_tests.py
```

---

## Common Issues

### 1. GUI Won't Launch

#### Symptom
```
[ERROR] PyWebView could not initialize a GUI backend
```

#### Cause
Missing PyWebView dependencies for your platform.

#### Fix

**Windows:**
```bash
pip install pywebview[cef]
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install python3-gi python3-gi-cairo gir1.2-webkit2-4.0
pip install pywebview[gtk]
```

**macOS:**
```bash
pip install pyobjc pywebview
```

**Alternative (all platforms):**
```bash
pip install pywebview[qt]  # Uses Qt5 backend
```

---

### 2. Death Loop (Infinite Terminal Scrolling)

#### Symptom
Terminal continuously shows:
```
[service(12345)] [ERROR] espanso is not running
[service(12346)] [ERROR] espanso is not running
[service(12347)] [ERROR] espanso is not running
...
```

#### Cause
- Espanso service failed to start
- GUI attempting to auto-start repeatedly (fixed in v1.0)

####Fix

**Option A: Start Espanso Manually**
```bash
espanso start
```

Then restart GUI:
```bash
python espansogui.py
```

**Option B: Check Espanso Installation**
```bash
espanso --version      # Should show version number
espanso status         # Should show "running" or "stopped"
```

**If espanso not found:**
- Windows: Reinstall from [espanso.org](https://espanso.org)
- Linux: `sudo apt install espanso` or build from source
- macOS: `brew install espanso`

**Option C: Update EspansoGUI**
Death loop fix implemented in Session 1B (2025-11-21). Update to latest version.

---

### 3. Snippets Not Expanding

#### Symptom
Type trigger (e.g., `:email`) but nothing happens.

#### Diagnosis Steps

**Step 1: Check Espanso Status**
```bash
espanso status
# Should show "espanso is running"
```

**Step 2: Check GUI Dashboard**
- Launch EspansoGUI
- Go to Dashboard
- Look at "Service Status"
- Should say "Connected" or "espanso is running"

**Step 3: Verify Snippet Exists**
- Go to Snippet Library
- Search for your trigger
- Confirm it's listed and enabled

**Step 4: Check Logs**
- Go to Logs tab in GUI
- Type your trigger in another app
- Watch for log entries
- Look for errors or warnings

#### Common Causes & Fixes

**A. Espanso Not Running**
```bash
espanso start
```

**B. Snippet Disabled**
- Open snippet in IDE
- Check "Enabled" checkbox
- Save and restart Espanso

**C. Trigger Conflict**
Two snippets with same trigger:
- Search for trigger in library
- Find duplicates
- Delete or rename one

**D. Wrong Application Context**
Snippet has `filter_exec` limiting to specific app:
- Edit snippet
- Remove app-specific filters
- Or use trigger in the correct app

**E. Recent Changes Not Applied**
```bash
# In GUI: Settings → Restart Espanso
# Or CLI:
espanso restart
```

---

### 4. Trigger Interference (Intermittent Failures)

#### Symptom
Snippets work sometimes but not always, even though Espanso is running.

#### Possible Causes

**A. SnippetSense Keyboard Hook**
SnippetSense monitors typing and may interfere:

**Fix:**
- Settings → SnippetSense → Disable
- Test triggers again
- If fixed, SnippetSense was the issue

**B. File Watcher Reload**
Config reloading mid-typing:

**Check:**
- Logs tab → Look for "Loaded X snippets" messages
- If frequent (every few seconds), reload is too aggressive

**Fix:**
- Fixed in v1.0 (2s debounce)
- Update to latest version

**C. Other Text Expansion Tools**
Running multiple text expanders:

**Fix:**
- Close TextExpander, aText, PhraseExpress, etc.
- Test Espanso alone

**D. High CPU/Memory**
System overloaded:

**Fix:**
- Close heavy applications
- Check Task Manager/Activity Monitor
- Restart Espanso and GUI

---

### 5. High Memory Usage

#### Symptom
EspansoGUI using >500MB RAM.

#### Causes

**A. Large Snippet Library**
1000+ snippets loaded into memory.

**Fix:**
- Split snippets across multiple files
- Use pagination (already enabled)
- Restart GUI periodically

**B. Circular Variable Dependencies**
Variable A references Variable B references Variable A.

**Fix:**
- Review global variables
- Remove circular references
- Test with `validate_regex` API

**C. File Watcher Overhead**
Monitoring too many directories:

**Fix:**
- Reduce imported files
- Use single match directory
- Disable watcher if not editing

---

### 6. YAML Syntax Errors

#### Symptom
```
[ERROR] YAML parse failed: ...
```

#### Common Mistakes

**A. Indentation**
YAML requires consistent spacing (use 2 spaces, never tabs).

**Wrong:**
```yaml
matches:
- trigger: ":test"
  replace: "value"
```

**Right:**
```yaml
matches:
  - trigger: ":test"
    replace: "value"
```

**B. Special Characters**
Quotes needed for colons, brackets, etc.

**Wrong:**
```yaml
replace: Time: 5:00 PM
```

**Right:**
```yaml
replace: "Time: 5:00 PM"
```

**C. Multiline Text**
Use `|` for multiline:

```yaml
replace: |
  Line 1
  Line 2
  Line 3
```

#### Validation
Use GUI's built-in validator:
- Edit snippet in IDE
- Save → Auto-validates YAML
- Shows errors before saving

---

### 7. Backup/Restore Issues

#### Can't Find Backups

**Check location:**
- Linux/Mac: `~/.config/espansogui/backups/`
- Windows: `%APPDATA%\espansogui\backups\`

**List backups:**
```bash
# In GUI: Settings → Backup & Restore
# Or manually:
ls ~/.config/espansogui/backups/
```

#### Restore Failed

**Cause:** Backup file corrupted or incompatible.

**Fix:**
- Try older backup
- Manually copy YAML files from backup
- Check backup file with text editor

---

### 8. Package Installation Errors

#### Symptom
```
[ERROR] Package install failed: ...
```

#### Fixes

**A. Network Issues**
```bash
# Test connection
ping hub.espanso.org

# Use proxy if needed
export HTTPS_PROXY=http://proxy:port
espanso package install <name>
```

**B. Permission Errors**
```bash
# Linux/Mac: Run with sudo
sudo espanso package install <name>

# Windows: Run as Administrator
```

**C. Package Not Found**
- Check package name spelling
- Search hub: https://hub.espanso.org
- Ensure package exists and is published

---

### 9. Form Snippets Not Working

#### Symptom
Form dialog doesn't appear when typing trigger.

#### Checks

**A. Form Syntax**
```yaml
matches:
  - trigger: ":form"
    form: |
      [[name]]
      [[email]]
    replace: "Name: {{name}}, Email: {{email}}"
```

**B. Form Fields Required**
At least one form field must exist.

**C. Backend Compatibility**
Forms require `inject` backend:
```yaml
backend: inject  # Not clipboard
```

---

### 10. WSL (Windows Subsystem for Linux) Issues

#### Symptom
GUI won't launch from WSL.

#### Cause
PyWebView requires X11 or WSLg.

#### Fixes

**Option A: Use WSLg** (Windows 11+)
Already built-in, should work automatically.

**Option B: Launch Windows Version**
GUI detects WSL and launches Windows host process automatically.

**Option C: X11 Server**
```bash
# Install VcXsrv or Xming
export DISPLAY=:0
python espansogui.py
```

**Option D: Run on Windows**
Copy project to Windows filesystem:
```bash
cp -r /mnt/c/Users/YourName/Projects/EspansoGUI
cd /mnt/c/Users/YourName/Projects/EspansoGUI
python espansogui.py
```

---

### 11. Import/Export Errors

#### Import Failed

**A. File Format**
- Must be `.json` or `.yaml`
- Must have correct structure

**B. Invalid Snippets**
- Missing `trigger` or `replace` fields
- Invalid variable syntax

**Fix:**
- Validate JSON/YAML with online validator
- Check example snippet packs in `/examples/`

#### Export Failed

**A. No Snippets Selected**
- Select at least one snippet
- Click checkboxes in library

**B. Permission Denied**
- Choose writable directory
- Check disk space

---

### 12. SnippetSense Not Suggesting

#### Symptom
Typed repeated phrases but no suggestions.

#### Checks

**A. Enabled**
Settings → SnippetSense → Toggle On

**B. Threshold Not Met**
Default: 3 repetitions within 7 days.

**Fix:**
- Lower "Repetition Threshold" to 2
- Type phrase more times

**C. App Not Whitelisted**
Windows only: App detection filters.

**Fix:**
- Add app to whitelist
- Or disable app filters

**D. Dependencies Missing**
```bash
pip install pynput psutil
```

---

## Platform-Specific Issues

### Windows

**Issue:** `.cmd` vs `.exe` confusion

**Fix:**
GUI automatically resolves this. If issues persist:
```bash
where espanso  # Should show espanso.exe
```

**Issue:** Antivirus blocking

**Fix:**
Add EspansoGUI and Espanso to antivirus exceptions.

---

### macOS

**Issue:** Permission denied for Accessibility

**Fix:**
- System Preferences → Security & Privacy → Accessibility
- Add Terminal.app or Python
- Restart

**Issue:** `pyobjc` installation fails

**Fix:**
```bash
brew install python-tk
pip3 install --upgrade pip setuptools
pip3 install pyobjc
```

---

### Linux

**Issue:** Wayland vs X11

Espanso works best on X11.

**Fix:**
Log out, select "Ubuntu on Xorg" at login screen.

**Issue:** Permission errors

**Fix:**
```bash
sudo usermod -aG input $USER
# Log out and back in
```

---

## Getting Help

### Collect Diagnostic Information

**1. Version Info**
```bash
python --version
espanso --version
pip show pywebview
```

**2. System Info**
```bash
# Linux/Mac
uname -a

# Windows
systeminfo | findstr /B /C:"OS Name" /C:"OS Version"
```

**3. Logs**
```bash
# Espanso logs
espanso log

# GUI logs (in GUI)
Logs tab → Copy all
```

**4. Test Results**
```bash
python smoke_check.py > diagnostic.txt 2>&1
python tests/run_tests.py >> diagnostic.txt 2>&1
```

### Report Issues

**GitHub Issues:** Include:
- OS and version
- Python version
- Espanso version
- EspansoGUI version
- Steps to reproduce
- Diagnostic logs
- Expected vs actual behavior

---

## Performance Tuning

### Reduce Startup Time

1. **Reduce snippet count:** Split large libraries
2. **Disable SnippetSense:** If not needed
3. **Disable file watcher:** Set polling interval higher

### Reduce Memory Usage

1. **Pagination:** Already enabled (50 per page)
2. **Cache cleanup:** Restart GUI periodically
3. **Limit backups:** Delete old backups

### Speed Up Snippets

1. **Use `inject` backend:** Faster than `clipboard`
2. **Reduce delay:** Default is 0ms, only increase if needed
3. **Simplify variables:** Complex shell commands slow expansion

---

## Advanced Debugging

### Enable Debug Logging

**Espanso:**
```bash
espanso --log-level debug start
```

**GUI:**
Edit `espansogui.py`, set `debug=True` in `webview.start()`.

### Inspect YAML Files

```bash
# View base config
cat ~/.config/espanso/config/default.yml

# View match files
cat ~/.config/espanso/match/base.yml
```

### Test CLI Directly

```bash
# Test espanso CLI
espanso status
espanso match list
espanso package list

# Test with Python
python -c "from core.cli_adapter import CLIAdapter; c=CLIAdapter(); print(c.run(['status']))"
```

---

## Still Stuck?

1. **Read USER_GUIDE.md** for feature documentation
2. **Check API_REFERENCE.md** for developers
3. **Review ARCHITECTURE.md** for design decisions
4. **Search closed issues** on GitHub
5. **Ask in Discussions** for community help

---

**Last Updated:** 2025-11-21
**Maintainer:** EspansoGUI Team
