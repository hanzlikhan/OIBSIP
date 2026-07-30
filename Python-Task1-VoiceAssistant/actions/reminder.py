"""
Reminder Action module.
Sets a background thread timer that triggers local hardware beep and WebSocket updates.
"""

import time
import threading
import sys
from actions.base import BaseAction
from core.nlu import INTENT_REMINDER

# Global registry of active reminders
active_reminders = []
active_reminders_lock = threading.Lock()

class ReminderThread(threading.Thread):
    def __init__(self, duration: int, message: str, trigger_callback=None):
        super().__init__()
        self.duration = duration
        self.message = message
        self.trigger_callback = trigger_callback
        self.start_time = time.time()
        self.end_time = self.start_time + duration
        self.daemon = True
        self.reminder_id = f"rem_{int(self.start_time)}_{duration}"

    def run(self):
        # Sleep until duration completes
        time.sleep(self.duration)
        
        # 1. Trigger local system beep alert
        try:
            # Winsound is native to Windows systems
            import winsound
            # Frequency = 1000Hz, Duration = 1500ms
            winsound.Beep(1000, 1500)
        except Exception:
            # Fallback beep
            print("\a", end="")

        # 2. Invoke WebSocket notification callback
        if self.trigger_callback:
            try:
                self.trigger_callback(self.reminder_id, self.message)
            except Exception as e:
                print(f"Error invoking reminder callback: {e}", file=sys.stderr)

        # 3. Clean up from active registry
        with active_reminders_lock:
            global active_reminders
            active_reminders = [r for r in active_reminders if r.reminder_id != self.reminder_id]

class ReminderAction(BaseAction):
    def __init__(self, ws_callback=None):
        """
        ws_callback: Function that accepts (reminder_id, message) to send to WebSocket clients.
        """
        self.ws_callback = ws_callback

    @property
    def name(self) -> str:
        return INTENT_REMINDER

    def execute(self, entities: dict) -> dict:
        duration = entities.get("duration", 0)
        message = entities.get("message", "Timer alert!").strip()

        if duration <= 0:
            return {
                "speech": "I couldn't understand the duration for the reminder. Please specify a time like five seconds or ten minutes.",
                "ui_data": {"status": "error"}
            }

        # Human-readable duration phrase
        duration_phrase = self._format_duration(duration)

        # Create and start the timer thread
        timer = ReminderThread(duration, message, self.ws_callback)
        
        with active_reminders_lock:
            active_reminders.append(timer)
            
        timer.start()

        speech_text = f"I've set a reminder in {duration_phrase} to {message}."
        
        return {
            "speech": speech_text,
            "ui_data": {
                "reminder_id": timer.reminder_id,
                "duration": duration,
                "message": message,
                "end_time_iso": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(timer.end_time)),
                "active_count": len(active_reminders)
            }
        }

    def _format_duration(self, seconds: int) -> str:
        """Helper to format seconds into friendly speech text."""
        if seconds < 60:
            return f"{seconds} second" + ("s" if seconds != 1 else "")
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        
        minutes_part = f"{minutes} minute" + ("s" if minutes != 1 else "")
        seconds_part = f" and {remaining_seconds} second" + ("s" if remaining_seconds != 1 else "") if remaining_seconds > 0 else ""
        
        return minutes_part + seconds_part

def get_active_reminders_list() -> list[dict]:
    """Helper to retrieve a list of running timers for the GUI dashboard."""
    now = time.time()
    list_reminders = []
    with active_reminders_lock:
        for r in active_reminders:
            time_left = max(0, int(r.end_time - now))
            list_reminders.append({
                "id": r.reminder_id,
                "message": r.message,
                "duration": r.duration,
                "time_left": time_left,
                "end_time": time.strftime('%H:%M:%S', time.localtime(r.end_time))
            })
    return list_reminders
