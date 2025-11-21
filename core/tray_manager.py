"""
Cross-platform system tray manager for EspansoGUI.

Provides minimize-to-tray functionality across Windows, Linux, and macOS.
Uses pystray library with Pillow for icon generation.
"""
from __future__ import annotations

import platform
import threading
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import pystray


class TrayManager:
    """Manages system tray icon and menu across platforms.

    Features:
    - Minimize to tray
    - Restore from tray (click or menu)
    - Quick status indicator
    - Exit application option

    Platform Notes:
    - Windows: Full support via Windows notification area
    - Linux: Requires AppIndicator or StatusNotifier support
    - macOS: Uses NSStatusBar (menu bar icon)
    """

    def __init__(
        self,
        on_show: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize tray manager.

        Args:
            on_show: Callback when user requests to show the window
            on_exit: Callback when user requests to exit the application
        """
        self._on_show = on_show
        self._on_exit = on_exit
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._platform = platform.system()

    def _create_icon_image(self):
        """Create a simple icon image programmatically.

        Returns an "E" icon for Espanso in brand colors.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            # Fallback: create minimal 16x16 icon
            from PIL import Image
            img = Image.new("RGBA", (64, 64), (76, 175, 80, 255))  # Green background
            return img

        # Create 64x64 icon with Espanso-style branding
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background circle (green - Espanso brand color)
        draw.ellipse([2, 2, size - 2, size - 2], fill=(76, 175, 80, 255))

        # Draw "E" for Espanso in white
        try:
            # Try to use a system font
            font = ImageFont.truetype("arial.ttf", 40)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            except (OSError, IOError):
                # Fallback to default font
                font = ImageFont.load_default()

        # Center the "E"
        text = "E"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - 4  # Slight adjustment for visual centering

        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

        return img

    def _create_menu(self):
        """Create the tray menu."""
        try:
            import pystray
        except ImportError:
            return None

        menu_items = [
            pystray.MenuItem("Show EspansoGUI", self._on_show_clicked, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Espanso Status", self._show_status),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._on_exit_clicked),
        ]
        return pystray.Menu(*menu_items)

    def _on_show_clicked(self, icon, item):
        """Handle show window request."""
        if self._on_show:
            self._on_show()

    def _on_exit_clicked(self, icon, item):
        """Handle exit request."""
        self.stop()
        if self._on_exit:
            self._on_exit()

    def _show_status(self, icon, item):
        """Show Espanso status notification."""
        try:
            import subprocess
            result = subprocess.run(
                ["espanso", "status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            status = result.stdout.strip() or result.stderr.strip() or "Unknown status"
            if icon:
                icon.notify(status, "Espanso Status")
        except Exception as e:
            if icon:
                icon.notify(f"Could not get status: {e}", "Espanso Status")

    def _run_tray(self):
        """Run the system tray icon (called in background thread)."""
        try:
            import pystray
        except ImportError:
            print("[WARN] pystray not installed. System tray disabled.", flush=True)
            return

        try:
            image = self._create_icon_image()
            menu = self._create_menu()

            self._icon = pystray.Icon(
                name="EspansoGUI",
                icon=image,
                title="EspansoGUI - Click to show",
                menu=menu
            )

            # On Windows/Linux, left-click shows the window
            if self._platform in ("Windows", "Linux"):
                self._icon.on_activate = lambda icon: self._on_show_clicked(icon, None)

            print("[INFO] System tray icon started", flush=True)
            self._running = True
            self._icon.run()
        except Exception as e:
            print(f"[WARN] System tray failed to start: {e}", flush=True)
            self._running = False

    def start(self) -> bool:
        """Start the system tray icon in a background thread.

        Returns:
            True if tray was started successfully, False otherwise.
        """
        if self._running:
            return True

        try:
            import pystray
        except ImportError:
            print("[WARN] pystray not available. Install with: pip install pystray pillow", flush=True)
            return False

        self._thread = threading.Thread(target=self._run_tray, daemon=True)
        self._thread.start()

        # Give it a moment to start
        import time
        time.sleep(0.5)

        return self._running

    def stop(self):
        """Stop the system tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
        self._running = False
        print("[INFO] System tray icon stopped", flush=True)

    def is_running(self) -> bool:
        """Check if tray icon is currently running."""
        return self._running

    def update_tooltip(self, text: str):
        """Update the tray icon tooltip text."""
        if self._icon:
            self._icon.title = text

    def notify(self, message: str, title: str = "EspansoGUI"):
        """Show a notification from the tray icon."""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass  # Notifications may not be supported on all platforms


# Singleton instance for easy access
_tray_manager: Optional[TrayManager] = None


def get_tray_manager(
    on_show: Optional[Callable[[], None]] = None,
    on_exit: Optional[Callable[[], None]] = None,
) -> TrayManager:
    """Get or create the global tray manager instance."""
    global _tray_manager
    if _tray_manager is None:
        _tray_manager = TrayManager(on_show=on_show, on_exit=on_exit)
    return _tray_manager


def cleanup_tray():
    """Clean up tray manager on application exit."""
    global _tray_manager
    if _tray_manager:
        _tray_manager.stop()
        _tray_manager = None
