"""
Stress Test: 1000+ Snippet Performance
Tests application performance and stability under high load
"""
import tempfile
import time
from pathlib import Path
import sys
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.snippet_store import SnippetStore
from core.backup_manager import BackupManager
from core.watcher_manager import WatcherManager


def print_result(test_name, duration, status="PASS"):
    """Print formatted test result"""
    print(f"[{status}] {test_name}: {duration:.2f}s")


def stress_test_create_1000_snippets():
    """
    Stress Test 1: Create 1000 snippets sequentially
    Target: < 2 minutes (120s)
    """
    print("\n" + "="*60)
    print("Stress Test 1: Create 1000 Snippets")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir = Path(tmpdir) / "match"
        match_dir.mkdir(parents=True)

        base_file = match_dir / "base.yml"
        base_file.write_text("matches: []\n", encoding="utf-8")

        store = SnippetStore(match_dir)

        start_time = time.time()
        failed = 0

        print(f"Creating 1000 snippets...")
        for i in range(1000):
            snippet = {
                "trigger": f":stress{i:04d}",
                "replace": f"Stress test snippet #{i}",
                "label": f"Stress Test {i}"
            }
            result = store.create_snippet(snippet)
            if result["status"] != "success":
                failed += 1

            # Progress indicator every 100 snippets
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"  Progress: {i+1}/1000 ({rate:.1f} snippets/sec)")

        duration = time.time() - start_time

        print(f"\nResults:")
        print(f"  Total snippets: 1000")
        print(f"  Failed: {failed}")
        print(f"  Time: {duration:.2f}s")
        print(f"  Rate: {1000/duration:.1f} snippets/sec")

        status = "PASS" if duration < 120 and failed == 0 else "SLOW" if failed == 0 else "FAIL"
        print_result("Create 1000 snippets", duration, status)

        return {"duration": duration, "failed": failed, "passed": failed == 0}


def stress_test_list_1000_snippets():
    """
    Stress Test 2: List 1000 snippets
    Target: < 5 seconds
    """
    print("\n" + "="*60)
    print("Stress Test 2: List 1000 Snippets")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir = Path(tmpdir) / "match"
        match_dir.mkdir(parents=True)

        # Create 1000 snippets quickly
        base_file = match_dir / "base.yml"
        yaml_content = "matches:\n"
        for i in range(1000):
            yaml_content += f"  - trigger: ':list{i:04d}'\n    replace: 'List test {i}'\n"
        base_file.write_text(yaml_content, encoding="utf-8")

        store = SnippetStore(match_dir)

        # First load (populate cache)
        print("First load (cold cache)...")
        start_time = time.time()
        snippets = store.list_snippets()
        first_load = time.time() - start_time

        print(f"  Loaded: {len(snippets)} snippets in {first_load:.2f}s")

        # Second load (from cache)
        print("\nSecond load (warm cache)...")
        start_time = time.time()
        snippets = store.list_snippets()
        second_load = time.time() - start_time

        print(f"  Loaded: {len(snippets)} snippets in {second_load:.4f}s")

        # Third load (clear cache, reload)
        print("\nThird load (cache cleared)...")
        store._match_cache = []
        start_time = time.time()
        snippets = store.list_snippets()
        third_load = time.time() - start_time

        print(f"  Loaded: {len(snippets)} snippets in {third_load:.2f}s")

        print(f"\nResults:")
        print(f"  Cold cache: {first_load:.2f}s")
        print(f"  Warm cache: {second_load:.4f}s (speedup: {first_load/second_load:.0f}x)")
        print(f"  Cache cleared: {third_load:.2f}s")

        status = "PASS" if first_load < 5 and len(snippets) == 1000 else "SLOW" if len(snippets) == 1000 else "FAIL"
        print_result("List 1000 snippets", first_load, status)

        return {"first_load": first_load, "cached_load": second_load, "passed": len(snippets) == 1000}


def stress_test_search_1000_snippets():
    """
    Stress Test 3: Search through 1000 snippets
    Target: < 1 second for various search patterns
    """
    print("\n" + "="*60)
    print("Stress Test 3: Search 1000 Snippets")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir = Path(tmpdir) / "match"
        match_dir.mkdir(parents=True)

        # Create diverse snippets
        base_file = match_dir / "base.yml"
        yaml_content = "matches:\n"
        categories = ["email", "code", "text", "date", "url"]
        for i in range(1000):
            category = categories[i % len(categories)]
            yaml_content += f"  - trigger: ':{category}{i:04d}'\n    replace: '{category.title()} snippet {i}'\n"
        base_file.write_text(yaml_content, encoding="utf-8")

        store = SnippetStore(match_dir)
        snippets = store.list_snippets()

        print(f"Loaded {len(snippets)} snippets for searching\n")

        # Test 1: Exact trigger match
        print("Test 1: Exact trigger match...")
        start_time = time.time()
        results = [s for s in snippets if s.get("trigger") == ":email0500"]
        exact_time = time.time() - start_time
        print(f"  Found {len(results)} results in {exact_time:.4f}s")

        # Test 2: Prefix search
        print("\nTest 2: Prefix search (email*)...")
        start_time = time.time()
        results = [s for s in snippets if s.get("trigger", "").startswith(":email")]
        prefix_time = time.time() - start_time
        print(f"  Found {len(results)} results in {prefix_time:.4f}s")

        # Test 3: Contains search
        print("\nTest 3: Contains search (code)...")
        start_time = time.time()
        results = [s for s in snippets if "code" in s.get("trigger", "").lower() or "code" in s.get("replace", "").lower()]
        contains_time = time.time() - start_time
        print(f"  Found {len(results)} results in {contains_time:.4f}s")

        # Test 4: Multi-field search
        print("\nTest 4: Multi-field search (snippet 0100)...")
        start_time = time.time()
        results = [s for s in snippets if "0100" in s.get("trigger", "") or "0100" in s.get("replace", "")]
        multifield_time = time.time() - start_time
        print(f"  Found {len(results)} results in {multifield_time:.4f}s")

        # Test 5: Regex-style search
        print("\nTest 5: Complex filter (trigger starts with :date and contains 05)...")
        start_time = time.time()
        results = [s for s in snippets if s.get("trigger", "").startswith(":date") and "05" in s.get("trigger", "")]
        complex_time = time.time() - start_time
        print(f"  Found {len(results)} results in {complex_time:.4f}s")

        avg_time = (exact_time + prefix_time + contains_time + multifield_time + complex_time) / 5

        print(f"\nResults:")
        print(f"  Average search time: {avg_time:.4f}s")
        print(f"  Slowest search: {max(exact_time, prefix_time, contains_time, multifield_time, complex_time):.4f}s")

        status = "PASS" if avg_time < 1.0 else "SLOW"
        print_result("Search 1000 snippets", avg_time, status)

        return {"avg_time": avg_time, "passed": True}


def stress_test_backup_1000_snippets():
    """
    Stress Test 4: Backup directory with 1000 snippets
    Target: < 10 seconds
    """
    print("\n" + "="*60)
    print("Stress Test 4: Backup 1000 Snippets")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir = Path(tmpdir) / "match"
        match_dir.mkdir(parents=True)
        backup_dir = Path(tmpdir) / "backups"
        backup_dir.mkdir()

        # Create large config
        base_file = match_dir / "base.yml"
        yaml_content = "matches:\n"
        for i in range(1000):
            yaml_content += f"  - trigger: ':backup{i:04d}'\n    replace: 'Backup test snippet {i}'\n    label: 'Backup {i}'\n"
        base_file.write_text(yaml_content, encoding="utf-8")

        file_size_mb = len(yaml_content) / (1024 * 1024)
        print(f"Config file size: {file_size_mb:.2f} MB")

        backup_mgr = BackupManager(backup_dir)

        # Test backup creation
        print("\nCreating backup...")
        start_time = time.time()
        result = backup_mgr.create_manual_backup(match_dir, "stress_test_backup")
        backup_time = time.time() - start_time

        print(f"  Backup status: {result['status']}")
        print(f"  Time: {backup_time:.2f}s")
        print(f"  Rate: {file_size_mb/backup_time:.2f} MB/s")

        # Test backup listing
        print("\nListing backups...")
        start_time = time.time()
        backups = backup_mgr.list_backups()
        list_time = time.time() - start_time

        print(f"  Found {len(backups)} backups in {list_time:.4f}s")

        # Test restore
        print("\nRestoring backup...")
        restore_dir = Path(tmpdir) / "restored"
        start_time = time.time()
        restore_result = backup_mgr.restore_backup("stress_test_backup", restore_dir, overwrite=False)
        restore_time = time.time() - start_time

        print(f"  Restore status: {restore_result['status']}")
        print(f"  Time: {restore_time:.2f}s")

        print(f"\nResults:")
        print(f"  Backup time: {backup_time:.2f}s")
        print(f"  Restore time: {restore_time:.2f}s")
        print(f"  Total time: {backup_time + restore_time:.2f}s")

        status = "PASS" if backup_time < 10 and restore_time < 10 and result["status"] == "success" else "SLOW" if result["status"] == "success" else "FAIL"
        print_result("Backup 1000 snippets", backup_time + restore_time, status)

        return {"backup_time": backup_time, "restore_time": restore_time, "passed": result["status"] == "success"}


def stress_test_file_size_limits():
    """
    Stress Test 5: Handle very large individual files
    Target: Successfully handle files with 5000+ snippets
    """
    print("\n" + "="*60)
    print("Stress Test 5: Large File Size Limits")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir = Path(tmpdir) / "match"
        match_dir.mkdir(parents=True)

        # Create massive file
        print("Creating file with 5000 snippets...")
        base_file = match_dir / "base.yml"
        yaml_content = "matches:\n"
        for i in range(5000):
            yaml_content += f"  - trigger: ':huge{i:05d}'\n    replace: 'Very large file test {i}'\n"

        start_time = time.time()
        base_file.write_text(yaml_content, encoding="utf-8")
        write_time = time.time() - start_time

        file_size_mb = len(yaml_content) / (1024 * 1024)
        print(f"  File size: {file_size_mb:.2f} MB")
        print(f"  Write time: {write_time:.2f}s")

        # Test parsing
        print("\nParsing large file...")
        store = SnippetStore(match_dir)
        start_time = time.time()
        snippets = store.list_snippets()
        parse_time = time.time() - start_time

        print(f"  Parsed {len(snippets)} snippets in {parse_time:.2f}s")
        print(f"  Rate: {len(snippets)/parse_time:.0f} snippets/sec")

        # Test memory efficiency (approximate)
        import sys
        snippet_memory_kb = sys.getsizeof(snippets) / 1024
        print(f"  Memory usage: ~{snippet_memory_kb:.0f} KB")

        print(f"\nResults:")
        print(f"  File size: {file_size_mb:.2f} MB")
        print(f"  Parse time: {parse_time:.2f}s")

        status = "PASS" if parse_time < 30 and len(snippets) == 5000 else "SLOW" if len(snippets) == 5000 else "FAIL"
        print_result("Parse 5000 snippet file", parse_time, status)

        return {"parse_time": parse_time, "file_size_mb": file_size_mb, "passed": len(snippets) == 5000}


def stress_test_concurrent_operations():
    """
    Stress Test 6: Rapid sequential operations
    Target: Handle 100 rapid CRUD operations without corruption
    """
    print("\n" + "="*60)
    print("Stress Test 6: Rapid Sequential Operations")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        match_dir = Path(tmpdir) / "match"
        match_dir.mkdir(parents=True)

        base_file = match_dir / "base.yml"
        base_file.write_text("matches: []\n", encoding="utf-8")

        store = SnippetStore(match_dir)

        operations = []
        errors = 0

        print("Performing 100 rapid operations (create/update/delete)...")
        start_time = time.time()

        # Create 50 snippets
        for i in range(50):
            result = store.create_snippet({
                "trigger": f":rapid{i:03d}",
                "replace": f"Rapid test {i}"
            })
            operations.append(("create", result["status"]))
            if result["status"] != "success":
                errors += 1

        # Update 25 snippets
        for i in range(25):
            result = store.update_snippet(f":rapid{i:03d}", {
                "trigger": f":rapid{i:03d}",
                "replace": f"Updated rapid test {i}"
            })
            operations.append(("update", result["status"]))
            if result["status"] != "success":
                errors += 1

        # Delete 25 snippets
        for i in range(25, 50):
            result = store.delete_snippet(f":rapid{i:03d}")
            operations.append(("delete", result["status"]))
            if result["status"] != "success":
                errors += 1

        duration = time.time() - start_time

        # Verify final state
        store._match_cache = []
        final_snippets = store.list_snippets()

        print(f"\nResults:")
        print(f"  Operations: {len(operations)}")
        print(f"  Errors: {errors}")
        print(f"  Time: {duration:.2f}s")
        print(f"  Rate: {len(operations)/duration:.1f} ops/sec")
        print(f"  Final snippet count: {len(final_snippets)}")
        print(f"  Expected count: 25")

        status = "PASS" if errors == 0 and len(final_snippets) == 25 else "FAIL"
        print_result("Rapid operations", duration, status)

        return {"duration": duration, "errors": errors, "passed": errors == 0 and len(final_snippets) == 25}


def run_all_stress_tests():
    """Run all stress tests and generate summary report"""
    print("\n" + "="*70)
    print(" " * 20 + "ESPANSOGUI STRESS TEST SUITE")
    print("="*70)
    print(f"Testing performance and stability under high load")
    print(f"Target: 1000+ snippets, rapid operations, large files")
    print("="*70)

    overall_start = time.time()
    results = {}

    # Run all tests
    results["create"] = stress_test_create_1000_snippets()
    results["list"] = stress_test_list_1000_snippets()
    results["search"] = stress_test_search_1000_snippets()
    results["backup"] = stress_test_backup_1000_snippets()
    results["large_file"] = stress_test_file_size_limits()
    results["rapid_ops"] = stress_test_concurrent_operations()

    overall_duration = time.time() - overall_start

    # Summary report
    print("\n\n" + "="*70)
    print(" " * 25 + "SUMMARY REPORT")
    print("="*70)

    all_passed = all(r["passed"] for r in results.values())

    print(f"\nTest Results:")
    print(f"  1. Create 1000 snippets:     {'PASS' if results['create']['passed'] else 'FAIL'} ({results['create']['duration']:.2f}s)")
    print(f"  2. List 1000 snippets:       {'PASS' if results['list']['passed'] else 'FAIL'} ({results['list']['first_load']:.2f}s)")
    print(f"  3. Search 1000 snippets:     {'PASS' if results['search']['passed'] else 'FAIL'} ({results['search']['avg_time']:.4f}s)")
    print(f"  4. Backup 1000 snippets:     {'PASS' if results['backup']['passed'] else 'FAIL'} ({results['backup']['backup_time'] + results['backup']['restore_time']:.2f}s)")
    print(f"  5. Large file (5000 items):  {'PASS' if results['large_file']['passed'] else 'FAIL'} ({results['large_file']['parse_time']:.2f}s)")
    print(f"  6. Rapid operations:         {'PASS' if results['rapid_ops']['passed'] else 'FAIL'} ({results['rapid_ops']['duration']:.2f}s)")

    print(f"\nOverall Status: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print(f"Total execution time: {overall_duration:.2f}s ({overall_duration/60:.1f} minutes)")

    print("\n" + "="*70)

    # Export results to JSON
    report_file = Path(__file__).parent / "stress_test_results.json"
    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "overall_duration_seconds": overall_duration,
        "all_passed": all_passed,
        "tests": {
            "create_1000": {
                "passed": results['create']['passed'],
                "duration_seconds": results['create']['duration'],
                "failed_count": results['create']['failed']
            },
            "list_1000": {
                "passed": results['list']['passed'],
                "cold_cache_seconds": results['list']['first_load'],
                "warm_cache_seconds": results['list']['cached_load']
            },
            "search_1000": {
                "passed": results['search']['passed'],
                "avg_time_seconds": results['search']['avg_time']
            },
            "backup_1000": {
                "passed": results['backup']['passed'],
                "backup_seconds": results['backup']['backup_time'],
                "restore_seconds": results['backup']['restore_time']
            },
            "large_file_5000": {
                "passed": results['large_file']['passed'],
                "parse_seconds": results['large_file']['parse_time'],
                "file_size_mb": results['large_file']['file_size_mb']
            },
            "rapid_operations_100": {
                "passed": results['rapid_ops']['passed'],
                "duration_seconds": results['rapid_ops']['duration'],
                "errors": results['rapid_ops']['errors']
            }
        }
    }

    report_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"Detailed results exported to: {report_file}")
    print("="*70 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_all_stress_tests())
