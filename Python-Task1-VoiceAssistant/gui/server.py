"""
FastAPI Server Module.
Establishes WebSocket routes for bi-directional front-end communication.
Runs Speech-to-Text and Assistant pipelines inside thread executors to remain non-blocking.
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from config.settings import settings
from core.assistant import VoiceAssistant
from core.audio import STTManager
from actions.reminder import get_active_reminders_list

# Setup Global Hotkey Listener Lifespan
hotkey_listener = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global hotkey_listener
    main_loop = asyncio.get_running_loop()
    
    def toggle_callback():
        # Dispatch HUD toggle event to WebSocket clients
        asyncio.run_coroutine_threadsafe(
            manager.send_json("toggle_hud", {}), 
            main_loop
        )
        
    from core.hotkey import HotkeyListener
    hotkey_listener = HotkeyListener(callback=toggle_callback)
    hotkey_listener.start()
    
    yield
    
    if hotkey_listener:
        hotkey_listener.stop()

# Setup FastAPI App with lifespan context manager
app = FastAPI(title="Nova Voice Assistant Dashboard", lifespan=lifespan)


# Paths
GUI_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = GUI_DIR / "templates"
STATIC_DIR = GUI_DIR / "static"

# Create static directories if they don't exist
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# HTML Template Renderer
@app.get("/")
async def get_dashboard():
    index_html = TEMPLATES_DIR / "index.html"
    if index_html.exists():
        with open(index_html, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content="<h1>Dashboard Template Not Found</h1>", status_code=404)


# Active WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_json(self, event_type: str, data: dict):
        payload = {"event": event_type, "data": data}
        for connection in self.active_connections:
            try:
                await connection.send_json(payload)
            except Exception:
                pass


manager = ConnectionManager()

# Instantiate STT engine
stt_manager = STTManager()

def get_settings_payload() -> dict:
    """Helper to structure system settings configuration for UI serialization."""
    from core.memory import memory_manager
    return {
        "weather_key": settings.WEATHER_API_KEY,
        "groq_key_set": bool(settings.GROQ_API_KEY),
        "groq_model": settings.NOVA_LLM_MODEL,
        "smtp_server": settings.SMTP_SERVER,
        "smtp_port": settings.SMTP_PORT,
        "smtp_user": settings.SMTP_USER,
        "smtp_from": settings.SMTP_FROM_EMAIL,
        "debug_mode": settings.DEBUG_MODE,
        "voice_rate": settings.DEFAULT_VOICE_RATE,
        "voice_gender": settings.DEFAULT_VOICE_GENDER,
        "custom_commands": settings.custom_commands,
        "active_reminders": get_active_reminders_list(),
        "memory_stats": memory_manager.get_stats()
    }


def save_environment_settings(data: dict):
    """Saves updated settings to runtime instance and writes them to local .env file."""
    settings.WEATHER_API_KEY = data.get("weather_key", "").strip()
    settings.SMTP_SERVER = data.get("smtp_server", "").strip()
    settings.SMTP_PORT = int(data.get("smtp_port", 587))
    settings.SMTP_USER = data.get("smtp_user", "").strip()
    settings.SMTP_FROM_EMAIL = data.get("smtp_from", "").strip()
    settings.DEBUG_MODE = bool(data.get("debug_mode", True))
    
    if "voice_rate" in data:
        settings.DEFAULT_VOICE_RATE = int(data["voice_rate"])
    if "voice_gender" in data:
        settings.DEFAULT_VOICE_GENDER = int(data["voice_gender"])

    # Persist back to the .env file in BASE_DIR
    env_path = settings.BASE_DIR / ".env"
    env_lines = []
    
    # Read existing lines if .env exists
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            env_lines = f.readlines()
            
    # Map of key-value pairs we want to write
    updates = {
        "OPENWEATHERMAP_API_KEY": settings.WEATHER_API_KEY,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "SMTP_SERVER": settings.SMTP_SERVER,
        "SMTP_PORT": str(settings.SMTP_PORT),
        "SMTP_USER": settings.SMTP_USER,
        "SMTP_FROM_EMAIL": settings.SMTP_FROM_EMAIL,
        "DEBUG_MODE": str(settings.DEBUG_MODE)
    }
    
    # Update lines in-place or append them
    new_lines = []
    processed_keys = set()
    
    for line in env_lines:
        match_found = False
        for key in updates.keys():
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={updates[key]}\n")
                processed_keys.add(key)
                match_found = True
                break
        if not match_found:
            new_lines.append(line)
            
    for key, value in updates.items():
        if key not in processed_keys:
            new_lines.append(f"{key}={value}\n")
            
    # Write back
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"Error saving updates to .env: {e}", file=sys.stderr)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Capture the main event loop running on this thread
    main_loop = asyncio.get_running_loop()
    
    # Setup assistant callback instance bound to this connection manager
    def ws_push(event: str, payload: dict):
        asyncio.run_coroutine_threadsafe(manager.send_json(event, payload), main_loop)

    assistant = VoiceAssistant(ws_send_callback=ws_push)

    try:
        # Push initial settings data to the UI on connection
        await websocket.send_json({"event": "settings_data", "data": get_settings_payload()})

        while True:
            # Receive incoming WS payloads
            data = await websocket.receive_text()
            message = json.loads(data)
            event_type = message.get("event")
            payload = message.get("data", {})

            if event_type == "user_input":
                # User typed a text command
                text_input = payload.get("text", "").strip()
                if text_input:
                    # Run assistant query processing in a separate thread so server loop is not blocked
                    await manager.send_json("status_change", {"status": "processing", "text": "Processing request..."})
                    result = await asyncio.to_thread(assistant.process_command, text_input)
                    await manager.send_json("assistant_response", result)
                    # Refresh reminders list in case a reminder was added/deleted
                    await manager.send_json("settings_data", get_settings_payload())

            elif event_type == "start_listening":
                # User clicked microphone button to record audio
                await manager.send_json("status_change", {"status": "listening", "text": "Listening..."})
                
                # Run blocking STT recorder in thread pool
                stt_result = await asyncio.to_thread(stt_manager.listen_and_transcribe)
                
                if stt_result["success"]:
                    transcription = stt_result["text"]
                    await manager.send_json("status_change", {"status": "processing", "text": f"Transcribed: '{transcription}'. Processing..."})
                    
                    # Run query processing
                    result = await asyncio.to_thread(assistant.process_command, transcription)
                    await manager.send_json("assistant_response", result)
                else:
                    err_code = stt_result["error_code"]
                    err_msg = "Could you repeat that? I didn't quite catch your voice."
                    
                    if err_code == "no_mic":
                        err_msg = "No microphone hardware detected on the server system. Please enter commands via text."
                    elif err_code == "service_error":
                        err_msg = "Speech recognition network service error. Please try again or use text input."
                    elif err_code == "timeout":
                        err_msg = "Speech recording timed out. No voice detected. Please try again."
                        
                    await manager.send_json("status_change", {"status": "idle", "text": ""})
                    await manager.send_json("error", {"message": err_msg, "code": err_code})

                # Refresh settings data (active reminders/commands)
                await manager.send_json("settings_data", get_settings_payload())

            elif event_type == "save_settings":
                # Save config updates
                save_environment_settings(payload)
                await manager.send_json("settings_data", get_settings_payload())
                await manager.send_json("notification", {"message": "System configurations saved successfully."})

            elif event_type == "save_command":
                # Add a custom command trigger
                trigger = payload.get("trigger", "").strip()
                response = payload.get("response", "").strip()
                if trigger and response:
                    settings.save_custom_command(trigger, response)
                    await manager.send_json("settings_data", get_settings_payload())
                    await manager.send_json("notification", {"message": f"Custom command '{trigger}' added."})

            elif event_type == "delete_command":
                # Remove a custom command
                trigger = payload.get("trigger", "").strip()
                if trigger:
                    settings.delete_custom_command(trigger)
                    await manager.send_json("settings_data", get_settings_payload())
                    await manager.send_json("notification", {"message": f"Custom command '{trigger}' removed."})

            elif event_type == "get_reminders":
                # Periodically sync running timers to frontend
                await manager.send_json("settings_data", get_settings_payload())

            elif event_type == "clear_session":
                # Clear LLM working memory (keeps long-term memory)
                msg = assistant.clear_session()
                await manager.send_json("notification", {"message": msg})
                await manager.send_json("session_cleared", {})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket execution exception: {e}", file=sys.stderr)
        manager.disconnect(websocket)
