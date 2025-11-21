# smoke_check.py - safe smoke test for espansogui shim
from pathlib import Path
import importlib
import sys
import traceback

p = Path('espansogui.py').resolve()
print('espansogui path:', p)
mod_name = 'espansogui'
importlib.invalidate_caches()
# ensure a clean import
if mod_name in sys.modules:
    del sys.modules[mod_name]

try:
    esp = importlib.import_module(mod_name)
    print('_prepare_gui_environment exists:', hasattr(esp, '_prepare_gui_environment'))
    print('_start_webview exists:', hasattr(esp, '_start_webview'))
    try:
        api = esp.EspansoAPI()
        print('EspansoAPI instantiated:', type(api))
        for a in ['list_snippets', 'search_snippets', 'platform']:
            print(f'has {a}:', hasattr(api, a))
    except Exception as e:
        print('EspansoAPI instantiation FAILED:', e)
        traceback.print_exc()
except Exception as e:
    print('Import failed:', e)
    traceback.print_exc()
