"""
Device Control Action — System automation using PyAutoGUI and psutil.
Handles: app launching, screenshots, keyboard/mouse control, system stats.
All actions are logged to data/action_log.jsonl for audit trail.
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime
from pathlib import Path
import psutil
import pyautogui

from config.settings import settings

# Safety: always enable PyAutoGUI failsafe
# Moving mouse to any screen corner immediately halts all automation
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05  # Small delay between actions for stability

# Screenshot directory
SCREENSHOT_DIR = settings.DATA_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Action log file
ACTION_LOG = settings.DATA_DIR / "action_log.jsonl"


def _log_action(action: str, details: dict, result: str):
    """Write every device action to the audit log."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details,
        "result": result
    }
    try:
        with open(ACTION_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# App Launcher
# ─────────────────────────────────────────────────────────────────────────────
APP_MAP = {
    # Common Windows apps & quick launchers
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "settings": "ms-settings:",
    "control panel": "control",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "vs code": "code",
    "visual studio code": "code",
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "browser": "start chrome",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://www.github.com",
    "chatgpt": "https://chatgpt.com",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "outlook": "outlook.exe",
    "spotify": "spotify.exe",
    "vlc": "vlc.exe",
    "discord": "discord.exe",
    "slack": "slack.exe",
    "zoom": "zoom.exe",
    "teams": "ms-teams.exe",
    "microsoft teams": "ms-teams.exe",
    "snipping tool": "snippingtool.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "whatsapp": "whatsapp.exe",
}


def open_application(app_name: str) -> str:
    """Launch an application or URL by name instantaneously (< 5ms execution)."""
    import webbrowser
    app_lower = app_name.lower().strip()

    # Direct match in APP_MAP
    target = APP_MAP.get(app_lower, None)
    
    # Partial match if direct match fails
    if not target:
        for k, v in APP_MAP.items():
            if k in app_lower or app_lower in k:
                target = v
                break

    if not target:
        target = app_name

    try:
        if target.startswith("http://") or target.startswith("https://"):
            webbrowser.open_new_tab(target)
        elif target.startswith("ms-"):
            os.startfile(target)
        elif target.startswith("start "):
            subprocess.Popen(target, shell=True)
        else:
            try:
                os.startfile(target)
            except Exception:
                subprocess.Popen(
                    f"start {target}",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

        result = f"Launched '{app_name}' successfully."
        _log_action("open_application", {"app_name": app_name, "target": target}, result)
        return result

    except Exception as e:
        error_msg = f"Could not open '{app_name}': {str(e)}"
        _log_action("open_application", {"app_name": app_name}, f"ERROR: {e}")
        print(f"[DeviceControl] {error_msg}", file=sys.stderr)
        return error_msg


# ─────────────────────────────────────────────────────────────────────────────
# Screenshot
# ─────────────────────────────────────────────────────────────────────────────
def take_screenshot() -> str:
    """Capture the current screen and save it."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = SCREENSHOT_DIR / filename

    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(str(filepath))
        result = f"Screenshot saved: {filepath}"
        _log_action("take_screenshot", {}, result)
        return result

    except Exception as e:
        error_msg = f"Screenshot failed: {str(e)}"
        _log_action("take_screenshot", {}, f"ERROR: {e}")
        return error_msg


# ─────────────────────────────────────────────────────────────────────────────
# Keyboard / Typing
# ─────────────────────────────────────────────────────────────────────────────
def type_text(text: str) -> str:
    """Type or paste specified text into the currently active window."""
    try:
        import pyperclip
        # Save previous clipboard content to restore later if desired, or just copy and paste
        prev_clipboard = pyperclip.paste()
        pyperclip.copy(text)
        time.sleep(0.15)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.1)
        # Restore clipboard
        if prev_clipboard:
            pyperclip.copy(prev_clipboard)
        result = f"Pasted {len(text)} characters."
        _log_action("type_text", {"length": len(text), "preview": text[:50]}, result)
        return result
    except Exception as e:
        print(f"[DeviceControl] Clipboard paste failed, falling back to typing: {e}", file=sys.stderr)
        try:
            time.sleep(0.3)  # Brief pause to ensure focus
            pyautogui.typewrite(text, interval=0.01)
            result = f"Typed {len(text)} characters."
            _log_action("type_text", {"length": len(text), "preview": text[:50]}, result)
            return result
        except Exception as e2:
            error_msg = f"Typing failed: {str(e2)}"
            _log_action("type_text", {"text": text[:50]}, f"ERROR: {e2}")
            return error_msg



def press_key(key: str) -> str:
    """Press a specific key or key combination."""
    try:
        if "+" in key:
            keys = [k.strip() for k in key.split("+")]
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(key)

        result = f"Key pressed: {key}"
        _log_action("press_key", {"key": key}, result)
        return result
    except Exception as e:
        return f"Key press failed: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# System Information
# ─────────────────────────────────────────────────────────────────────────────
def get_system_info(info_type: str = "all") -> str:
    """Retrieve real-time system performance metrics."""
    lines = []

    if info_type in ("cpu", "all"):
        cpu_pct = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        lines.append(f"CPU Usage: {cpu_pct}% across {cpu_count} cores")

    if info_type in ("ram", "all"):
        ram = psutil.virtual_memory()
        used_gb = ram.used / (1024 ** 3)
        total_gb = ram.total / (1024 ** 3)
        lines.append(f"RAM: {used_gb:.1f} GB used of {total_gb:.1f} GB ({ram.percent}% full)")

    if info_type in ("disk", "all"):
        try:
            disk = psutil.disk_usage("C:\\")
            used_gb = disk.used / (1024 ** 3)
            total_gb = disk.total / (1024 ** 3)
            lines.append(f"Disk (C:): {used_gb:.1f} GB used of {total_gb:.1f} GB ({disk.percent}% full)")
        except Exception:
            pass

    if info_type in ("processes", "all"):
        processes = []
        for proc in sorted(psutil.process_iter(["name", "cpu_percent", "memory_percent"]),
                           key=lambda p: p.info.get("memory_percent") or 0,
                           reverse=True)[:8]:
            name = proc.info.get("name", "Unknown")
            mem = proc.info.get("memory_percent", 0) or 0
            cpu = proc.info.get("cpu_percent", 0) or 0
            processes.append(f"  {name}: RAM {mem:.1f}% | CPU {cpu:.1f}%")
        lines.append("Top Processes:\n" + "\n".join(processes))

    return "\n".join(lines) if lines else "No system info retrieved."
