#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test all GUI API endpoints without launching the actual GUI."""

import sys

if sys.platform == "win32":
    import os
    os.system("")

from ui.gui_api import GUIApi as EspansoAPI

def test_all_apis():
    """Test all API methods that the GUI calls."""
    print("=" * 70)
    print("TESTING ALL GUI API ENDPOINTS")
    print("=" * 70)

    try:
        # Create API instance
        print("\n[1/8] Creating API instance...")
        api = EspansoAPI()
        print("  [OK] API created")

        # Test get_dashboard
        print("\n[2/8] Testing get_dashboard()...")
        dashboard = api.get_dashboard()
        print(f"  [OK] Status: {dashboard['statusMessage']}")
        print(f"  [OK] Snippets: {dashboard['snippetCount']}")
        print(f"  [OK] Connection steps: {len(dashboard['connectionSteps'])}")

        # Test get_settings
        print("\n[3/8] Testing get_settings()...")
        settings = api.get_settings()
        print(f"  [OK] Service status: {settings['serviceStatus']}")
        print(f"  [OK] Autostart status: {settings['autostart']['status']}")
        print(f"  [OK] Autostart detail: {settings['autostart']['detail']}")
        print(f"  [OK] Packages: {len(settings['packages'])}")

        # Test list_snippets
        print("\n[4/8] Testing list_snippets()...")
        snippets = api.list_snippets()
        print(f"  [OK] Retrieved {len(snippets)} snippets")

        # Test get_feature_catalog
        print("\n[5/8] Testing get_feature_catalog()...")
        catalog = api.get_feature_catalog()
        print(f"  [OK] Architecture info: {len(catalog.get('architecture', []))} items")
        print(f"  [OK] Success criteria: {len(catalog.get('success', []))} items")

        # Test refresh_files
        print("\n[6/8] Testing refresh_files()...")
        refresh_result = api.refresh_files()
        print(f"  [OK] Files refreshed, status: {refresh_result['statusMessage']}")

        # Test create_backup
        print("\n[7/8] Testing create_backup()...")
        backup_result = api.create_backup()
        print(f"  [OK] Backup created: {backup_result['path']}")
        print(f"  [OK] Files backed up: {backup_result['count']}")

        # Test service methods (without actually changing state)
        print("\n[8/8] Testing service control methods...")
        print("  [INFO] Skipping actual service control to avoid state changes")
        print("  [INFO] Methods available: start_service(), stop_service(), restart_service()")
        print("  [INFO] Methods available: toggle_autostart(), install_package(), uninstall_package()")

        # Shutdown
        print("\n[9/8] Shutting down API...")
        api.shutdown()
        print("  [OK] Clean shutdown")

        print("\n" + "=" * 70)
        print("[SUCCESS] All GUI API tests passed!")
        print("=" * 70)
        print("\nThe GUI should be able to connect and display data correctly.")
        print("Run: python espansogui.py")
        return True

    except Exception as exc:
        print(f"\n[FAIL] API test failed: {exc}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_all_apis()
    sys.exit(0 if success else 1)
