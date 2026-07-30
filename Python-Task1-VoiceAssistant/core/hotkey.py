"""
Global Hotkey Listener for Nova 2.1.
Listens for Ctrl+Shift+Space to toggle the Nova assistant overlay.
"""

import threading
import sys
import time

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False


class HotkeyListener:
    """Manages background hotkey listening."""

    def __init__(self, callback=None):
        self.callback = callback
        self.thread = None
        self.running = False

    def start(self):
        """Start listening for the global hotkey in a background thread."""
        if not HAS_KEYBOARD:
            print("[Hotkey] keyboard library not installed. Global hotkey disabled.", file=sys.stderr)
            return

        if self.thread and self.thread.is_alive():
            return

        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, name="NovaHotkeyThread", daemon=True)
        self.thread.start()
        print("[Hotkey] Global hotkey listener started (Ctrl+Shift+Space).")

    def stop(self):
        """Stop hotkey listening."""
        self.running = False
        try:
            if HAS_KEYBOARD:
                keyboard.unhook_all()
        except Exception:
            pass

    def _listen_loop(self):
        """Background hotkey polling/events listener."""
        try:
            # Register hotkey
            keyboard.add_hotkey("ctrl+shift+space", self._on_hotkey_pressed)
            
            # Simple wait loop to keep thread alive
            while self.running:
                time.sleep(0.5)
        except Exception as e:
            print(f"[Hotkey] Listener thread error: {e}", file=sys.stderr)
            self.running = False

    def _on_hotkey_pressed(self):
        """Fired when the global hotkey is pressed."""
        print("[Hotkey] Global hotkey (Ctrl+Shift+Space) triggered.")
        if self.callback:
            try:
                self.callback()
            except Exception as e:
                print(f"[Hotkey] Callback invocation failed: {e}", file=sys.stderr)
