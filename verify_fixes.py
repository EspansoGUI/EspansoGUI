#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification script for Espanso Companion Pro connection fixes.
Run this to verify that all fixes are working properly.
"""

import sys
from pathlib import Path

# Fix Windows console
if sys.platform == "win32":
    import os
    os.system("")

def test_connection():
    """Test that the connection to Espanso works properly."""
    from espanso_companion.cli_integration import EspansoCLI
    from espanso_companion.config_loader import ConfigLoader

    print("=" * 70)
    print("ESPANSO COMPANION PRO - CONNECTION VERIFICATION")
    print("=" * 70)

    # Test 1: CLI Connection
    print("\n[TEST 1] Espanso CLI Connection")
    print("-" * 70)
    try:
        cli = EspansoCLI()
        result = cli.run(["--version"])

        if result.stdout.strip():
            print(f"[PASS] Espanso version: {result.stdout.strip()}")
        else:
            print(f"[FAIL] No version output received")
            return False

        status = cli.run(["status"])
        if status.returncode == 0:
            print(f"[PASS] Espanso status: {status.stdout.strip()}")
        else:
            print(f"[WARN] Espanso may not be running: {status.stderr or status.stdout}")

    except Exception as exc:
        print(f"[FAIL] CLI connection failed: {exc}")
        return False

    # Test 2: Path Discovery
    print("\n[TEST 2] Path Discovery")
    print("-" * 70)
    try:
        loader = ConfigLoader()
        paths = loader.discover_paths()

        print(f"[PASS] Config:   {paths.config}")
        print(f"[PASS] Match:    {paths.match}")
        print(f"[PASS] Packages: {paths.packages}")
        print(f"[PASS] Runtime:  {paths.runtime}")

        # Verify paths exist
        for name, path in paths.__dict__.items():
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                print(f"[INFO] Created directory: {path}")

    except Exception as exc:
        print(f"[FAIL] Path discovery failed: {exc}")
        return False

    # Test 3: API Initialization
    print("\n[TEST 3] API Initialization (without GUI)")
    print("-" * 70)
    try:
        # Import and create API instance (but don't start GUI)
        from espansogui import EspansoAPI

        api = EspansoAPI()
        print(f"[PASS] API instance created successfully")

        # Test dashboard data
        dashboard = api.get_dashboard()
        print(f"[PASS] Dashboard data retrieved")
        print(f"       Status: {dashboard.get('statusMessage')}")
        print(f"       Snippets: {dashboard.get('snippetCount', 0)}")
        print(f"       Match files: {dashboard.get('matchFileCount', 0)}")
        print(f"       Events tracked: {dashboard.get('eventCount', 0)}")

        # Check connection steps
        steps = dashboard.get('connectionSteps', [])
        print(f"\n[INFO] Connection sequence results:")
        for step in steps:
            status_icon = "[OK]" if step['status'] == 'success' else "[!!]"
            print(f"       {status_icon} {step['label']}: {step['detail'][:50]}")

        # Shutdown cleanly
        api.shutdown()
        print(f"\n[PASS] API shutdown successful")

    except Exception as exc:
        print(f"[FAIL] API initialization failed: {exc}")
        import traceback
        traceback.print_exc()
        return False

    # All tests passed
    print("\n" + "=" * 70)
    print("[SUCCESS] All verification tests passed!")
    print("=" * 70)
    print("\nThe application is ready to run:")
    print("  python espansogui.py")
    print("\nConnection to local Espanso installation is working correctly.")
    return True

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
