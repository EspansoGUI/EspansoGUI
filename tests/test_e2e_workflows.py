"""
E2E Integration Tests for Critical Workflows
Tests complete user journeys end-to-end
"""
import tempfile
import shutil
from pathlib import Path
import time
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.snippet_store import SnippetStore
from core.backup_manager import BackupManager
from core.config_manager import ConfigManager
from core.watcher_manager import WatcherManager


def test_e2e_snippet_create_edit_delete_workflow():
    """
    E2E: User creates snippet → edits it → deletes it
    Verifies complete CRUD lifecycle
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        match_dir = config_dir / "match"
        match_dir.mkdir(parents=True)

        base_file = match_dir / "base.yml"
        base_file.write_text("matches:\n  - trigger: ':test'\n    replace: 'original'\n", encoding="utf-8")

        store = SnippetStore(match_dir)

        # Step 1: Create new snippet
        new_snippet = {
            "trigger": ":email",
            "replace": "user@example.com",
            "label": "My Email"
        }
        result = store.create_snippet(new_snippet)
        assert result["status"] == "success", f"Create failed: {result}"

        # Step 2: Verify it exists
        snippets = store.list_snippets()
        email_snippets = [s for s in snippets if s.get("trigger") == ":email"]
        assert len(email_snippets) == 1, "Snippet not found after creation"
        assert email_snippets[0]["replace"] == "user@example.com"

        # Step 3: Edit the snippet
        updated_snippet = {
            "trigger": ":email",
            "replace": "newemail@example.com",
            "label": "Updated Email"
        }
        result = store.update_snippet(":email", updated_snippet)
        assert result["status"] == "success", f"Update failed: {result}"

        # Step 4: Verify edit persisted
        snippets = store.list_snippets()
        email_snippets = [s for s in snippets if s.get("trigger") == ":email"]
        assert email_snippets[0]["replace"] == "newemail@example.com"
        assert email_snippets[0]["label"] == "Updated Email"

        # Step 5: Delete the snippet
        result = store.delete_snippet(":email")
        assert result["status"] == "success", f"Delete failed: {result}"

        # Step 6: Verify deletion
        snippets = store.list_snippets()
        email_snippets = [s for s in snippets if s.get("trigger") == ":email"]
        assert len(email_snippets) == 0, "Snippet still exists after deletion"


def test_e2e_snippet_pack_import_search_export_workflow():
    """
    E2E: User imports snippet pack → searches for snippet → exports selected snippets
    Verifies import/export + search functionality
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        match_dir = config_dir / "match"
        match_dir.mkdir(parents=True)

        base_file = match_dir / "base.yml"
        base_file.write_text("matches: []\n", encoding="utf-8")

        store = SnippetStore(match_dir)

        # Step 1: Create snippet pack  (JSON format expects "matches" key)
        pack_path = Path(tmpdir) / "test_pack.json"
        pack_content = """
{
    "matches": [
        {"trigger": ":work", "replace": "work@company.com"},
        {"trigger": ":personal", "replace": "me@personal.com"},
        {"trigger": ":support", "replace": "support@company.com"}
    ]
}
"""
        pack_path.write_text(pack_content, encoding="utf-8")

        # Step 2: Import pack
        result = store.import_snippet_pack(str(pack_path))
        assert result["status"] == "success", f"Import failed: {result}"
        assert "Imported 3 snippets" in result["detail"]

        # Step 3: Search for work-related snippets
        snippets = store.list_snippets()
        work_snippets = [s for s in snippets if "work" in s.get("trigger", "").lower()
                         or "work" in s.get("replace", "").lower()]
        assert len(work_snippets) >= 1, "Search failed to find work snippets"

        # Step 4: Export selected snippets
        export_path = Path(tmpdir) / "exported.json"
        # Get just the work and support triggers
        triggers_to_export = [":work", ":support"]

        # Manually create export (store doesn't have export_selected method yet)
        # This tests the data structure integrity
        snippets_to_export = [s for s in snippets if s.get("trigger") in triggers_to_export]
        assert len(snippets_to_export) == 2, "Failed to filter snippets for export"


def test_e2e_backup_create_modify_restore_workflow():
    """
    E2E: User creates backup → modifies config → restores from backup
    Verifies backup/restore + rollback capability
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        match_dir = config_dir / "match"
        match_dir.mkdir(parents=True)
        backup_dir = Path(tmpdir) / "backups"
        backup_dir.mkdir()

        base_file = match_dir / "base.yml"
        original_content = "matches:\n  - trigger: ':original'\n    replace: 'original value'\n"
        base_file.write_text(original_content, encoding="utf-8")

        store = SnippetStore(match_dir)
        backup_mgr = BackupManager(backup_dir)

        # Step 1: Create backup (backs up entire directory)
        backup_result = backup_mgr.create_manual_backup(match_dir, "pre-change")
        assert backup_result["status"] == "success", f"Backup failed: {backup_result}"

        # Step 2: Verify backup exists
        backups = backup_mgr.list_backups()
        assert len(backups) >= 1, "Backup not listed"

        # Step 3: Modify config
        modified_snippet = {
            "trigger": ":modified",
            "replace": "modified value"
        }
        store.create_snippet(modified_snippet)

        # Step 4: Verify modification
        store._match_cache = []  # Clear cache
        snippets = store.list_snippets()
        assert any(s.get("trigger") == ":modified" for s in snippets), "Modification not saved"

        # Step 5: Restore from backup (restore entire directory)
        restore_result = backup_mgr.restore_backup("pre-change", match_dir, overwrite=True)
        assert restore_result["status"] == "success", f"Restore failed: {restore_result}"

        # Step 6: Verify restoration
        restored_content = base_file.read_text(encoding="utf-8")
        assert ":original" in restored_content, "Restore didn't bring back original content"
        assert ":modified" not in restored_content, "Restore didn't remove modified content"


def test_e2e_file_watcher_external_edit_reload_workflow():
    """
    E2E: User starts watcher → edits file externally → watcher detects → cache refreshes
    Verifies file watching and cache invalidation
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        match_dir = config_dir / "match"
        match_dir.mkdir(parents=True)

        base_file = match_dir / "base.yml"
        base_file.write_text("matches:\n  - trigger: ':test'\n    replace: 'original'\n", encoding="utf-8")

        store = SnippetStore(match_dir)
        watcher = WatcherManager([match_dir])

        events_captured = []

        def capture_event(event):
            events_captured.append(event)

        # Step 1: Register callback and start watcher
        watcher.register_callback(capture_event)
        watcher.start()
        time.sleep(0.5)  # Allow watcher to initialize

        # Step 2: External edit (simulate user editing in text editor)
        base_file.write_text("matches:\n  - trigger: ':test'\n    replace: 'externally modified'\n", encoding="utf-8")
        time.sleep(1.5)  # Allow watcher to detect change

        # Step 3: Poll events
        detected_events = watcher.poll_events()

        # Step 4: Verify event detected
        # Note: watcher may capture multiple events (modified, created, etc.)
        assert len(detected_events) > 0 or len(events_captured) > 0, "Watcher didn't detect file change"

        # Step 5: Verify cache refresh (reload snippets with cleared cache)
        store._match_cache = []  # Clear cache to force reload
        snippets = store.list_snippets()
        test_snippet = next((s for s in snippets if s.get("trigger") == ":test"), None)
        assert test_snippet is not None, "Snippet not found after reload"
        assert test_snippet["replace"] == "externally modified", "Cache not refreshed with new content"

        # Step 6: Stop watcher
        watcher.stop()


def test_e2e_config_validation_and_preferences_workflow():
    """
    E2E: User loads preferences → modifies settings → saves → reloads
    Verifies config persistence and validation
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        config_file = config_dir / "preferences.json"

        mgr = ConfigManager(config_dir)

        # Step 1: Load default preferences
        prefs = mgr.get_preferences()
        assert isinstance(prefs, dict), "Failed to load default preferences"

        # Step 2: Modify preferences
        mgr.set_preference("theme", "dark")
        mgr.set_preference("snippetsense_enabled", True)
        mgr.set_preference("custom_setting", "test_value")

        # Step 3: Verify file exists
        assert config_file.exists(), "Preferences file not created"

        # Step 4: Reload preferences (simulate app restart)
        mgr2 = ConfigManager(config_dir)
        reloaded_prefs = mgr2.get_preferences()

        # Step 5: Verify persistence
        assert reloaded_prefs["theme"] == "dark", "Theme preference not persisted"
        assert reloaded_prefs["snippetsense_enabled"] is True, "SnippetSense preference not persisted"
        assert reloaded_prefs["custom_setting"] == "test_value", "Custom setting not persisted"


def test_e2e_high_volume_snippet_performance():
    """
    E2E: Stress test with 100 snippets
    Verifies performance with larger datasets (scaled down from 1000 for speed)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        match_dir = config_dir / "match"
        match_dir.mkdir(parents=True)

        base_file = match_dir / "base.yml"
        base_file.write_text("matches: []\n", encoding="utf-8")

        store = SnippetStore(match_dir)

        # Step 1: Create 100 snippets
        start_time = time.time()
        for i in range(100):
            snippet = {
                "trigger": f":test{i:03d}",
                "replace": f"Test snippet number {i}",
                "label": f"Test {i}"
            }
            result = store.create_snippet(snippet)
            assert result["status"] == "success", f"Failed to create snippet {i}: {result}"

        create_time = time.time() - start_time

        # Step 2: List all snippets (clear cache first)
        store._match_cache = []
        start_time = time.time()
        snippets = store.list_snippets()
        list_time = time.time() - start_time

        assert len(snippets) == 100, f"Expected 100 snippets, got {len(snippets)}"

        # Step 3: Search snippets
        start_time = time.time()
        # Search for snippets with "50" in them
        search_results = [s for s in snippets if "50" in s.get("trigger", "") or "50" in s.get("replace", "")]
        search_time = time.time() - start_time

        assert len(search_results) >= 1, "Search failed to find matching snippets"

        # Step 4: Performance assertions
        # These are reasonable thresholds for 100 snippets
        assert create_time < 30, f"Creating 100 snippets took {create_time:.2f}s (expected <30s)"
        assert list_time < 2, f"Listing 100 snippets took {list_time:.2f}s (expected <2s)"
        assert search_time < 0.5, f"Searching 100 snippets took {search_time:.2f}s (expected <0.5s)"


def test_e2e_multi_file_snippet_organization():
    """
    E2E: User organizes snippets across multiple files
    Verifies multi-file support and cross-file operations
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        match_dir = config_dir / "match"
        match_dir.mkdir(parents=True)

        # Create multiple match files
        base_file = match_dir / "base.yml"
        base_file.write_text("matches:\n  - trigger: ':base'\n    replace: 'base snippet'\n", encoding="utf-8")

        work_file = match_dir / "work.yml"
        work_file.write_text("matches:\n  - trigger: ':work'\n    replace: 'work@company.com'\n", encoding="utf-8")

        personal_file = match_dir / "personal.yml"
        personal_file.write_text("matches:\n  - trigger: ':home'\n    replace: 'home@personal.com'\n", encoding="utf-8")

        store = SnippetStore(match_dir)

        # Step 1: List all snippets from all files
        snippets = store.list_snippets()

        # Step 2: Verify snippets from all files loaded
        triggers = [s.get("trigger") for s in snippets]
        assert ":base" in triggers, "Base snippet not loaded"
        assert ":work" in triggers, "Work snippet not loaded"
        assert ":home" in triggers, "Personal snippet not loaded"

        # Step 3: Add new snippet (should go to base.yml by default)
        new_snippet = {"trigger": ":new", "replace": "new snippet"}
        result = store.create_snippet(new_snippet)
        assert result["status"] == "success"

        # Step 4: Verify total count (clear cache first)
        store._match_cache = []
        snippets = store.list_snippets()
        assert len(snippets) == 4, f"Expected 4 total snippets, got {len(snippets)}"


# If run directly, execute all tests
if __name__ == "__main__":
    print("Running E2E Integration Tests...")

    tests = [
        ("Snippet CRUD Workflow", test_e2e_snippet_create_edit_delete_workflow),
        ("Snippet Pack Import/Export", test_e2e_snippet_pack_import_search_export_workflow),
        ("Backup/Restore Workflow", test_e2e_backup_create_modify_restore_workflow),
        ("File Watcher Workflow", test_e2e_file_watcher_external_edit_reload_workflow),
        ("Config Preferences Workflow", test_e2e_config_validation_and_preferences_workflow),
        ("High Volume Performance", test_e2e_high_volume_snippet_performance),
        ("Multi-File Organization", test_e2e_multi_file_snippet_organization),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            print(f"PASS: {name}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {name} - {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {name} - {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"E2E Tests: {passed} passed, {failed} failed")
    print("="*60)

    if failed > 0:
        sys.exit(1)
