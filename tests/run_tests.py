import importlib.util
import inspect
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT.parent))

failed = 0
passed = 0

for path in sorted(ROOT.glob('test_*.py')):
    name = path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for obj_name, obj in inspect.getmembers(module):
        if obj_name.startswith('test_') and inspect.isfunction(obj):
            try:
                obj()
                print(f"PASS: {name}.{obj_name}")
                passed += 1
            except AssertionError as e:
                print(f"FAIL: {name}.{obj_name} - AssertionError: {e}")
                failed += 1
            except Exception as e:
                print(f"ERROR: {name}.{obj_name} - Exception: {e}")
                failed += 1

print('---')
print(f'Passed: {passed}, Failed: {failed}')
if failed:
    sys.exit(1)
