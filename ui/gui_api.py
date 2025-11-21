from __future__ import annotations

from typing import Any, Dict, List

from espansogui import EspansoAPI as LegacyEspansoAPI


class GUIApi(LegacyEspansoAPI):
    """Facade that exposes `EspansoAPI` through a dedicated API module.

    This exists so GUI-facing code and tests can import a clean `GUIApi`
    implementation while the monolithic `EspansoAPI` remains the source of truth.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    # Additional GUI-only helpers or adapters can be added here when the refactor
    # matures and the core modules are gradually adopted.

