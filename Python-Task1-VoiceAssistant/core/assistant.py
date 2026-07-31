"""
Nova AI Agent — Master Orchestrator (Nova 2.0)
Connects the Groq LLM brain to all action tools and memory.
Replaces the old keyword-matching NLU with genuine AI reasoning.
"""

import datetime
import sys
from config.settings import settings
from core.brain import NovaBrain
from core.memory import memory_manager
from core import audio

# ── Action Imports ─────────────────────────────────────────────────────────
from actions.web_search import web_search, search_news
from actions.device_control import (
    open_application, take_screenshot, type_text, get_system_info, press_key
)
from actions.browser_automation import browser_action
from actions.reminder import ReminderAction
from actions.weather import WeatherAction
from actions.email_sender import EmailSenderAction


class VoiceAssistant:
    """
    Nova 2.0 — AI Agent Orchestrator.
    The LLM brain autonomously selects and calls the right tools.
    """

    def __init__(self, ws_send_callback=None):
        """
        ws_send_callback: push events to the WebSocket UI.
                          Signature: ws_send_callback(event_type: str, data: dict)
        """
        self.ws_send_callback = ws_send_callback

        # ── Shared action instances ────────────────────────────────────────
        self._reminder_action = ReminderAction(
            ws_callback=self._on_reminder_triggered
        )
        self._weather_action = WeatherAction()
        self._email_action = EmailSenderAction()

        # ── Initialize brain with tool executor and activity feed ──────────
        self.brain = NovaBrain(
            tool_executor=self._execute_tool,
            ws_activity_callback=self._on_activity
        )

    # ── Event Callbacks ────────────────────────────────────────────────────

    def _push(self, event: str, data: dict):
        """Safe WebSocket push helper."""
        if self.ws_send_callback:
            try:
                self.ws_send_callback(event, data)
            except Exception as e:
                print(f"[Assistant] WS push error: {e}", file=sys.stderr)

    def _on_activity(self, step_type: str, message: str):
        """Relay LLM thinking steps to the UI activity feed."""
        self._push("activity_feed", {"type": step_type, "message": message})

    def _on_reminder_triggered(self, reminder_id: str, message: str):
        """Called when a background timer fires."""
        self._push("reminder_triggered", {
            "id": reminder_id,
            "message": message,
            "triggered_at": datetime.datetime.now().strftime("%H:%M:%S")
        })

    # ── Tool Executor — routes LLM tool calls to real Python functions ─────

    def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """
        Called by NovaBrain whenever the LLM decides to use a tool.
        Maps tool names to actual Python function implementations.
        """
        if not isinstance(tool_args, dict):
            tool_args = {}

        print(f"[Tool] Executing: {tool_name}({tool_args})")

        try:
            # ── Internet & Information ─────────────────────────────────────
            if tool_name == "web_search":
                return web_search(
                    query=tool_args.get("query", ""),
                    fetch_page=tool_args.get("fetch_page", False)
                )

            elif tool_name == "get_time_and_date":
                now = datetime.datetime.now()
                return (
                    f"Current time: {now.strftime('%I:%M %p')}, "
                    f"Date: {now.strftime('%A, %B %d, %Y')}"
                )

            elif tool_name == "get_weather":
                city = tool_args.get("city", "").strip()
                result = self._weather_action.execute({"location": city})
                return result.get("speech", "Weather data unavailable.")

            # ── Memory ─────────────────────────────────────────────────────
            elif tool_name == "save_memory":
                key = tool_args.get("key", "")
                value = tool_args.get("value", "")
                return memory_manager.save_fact(key, value)

            elif tool_name == "recall_memory":
                query = tool_args.get("query", "")
                return memory_manager.search_memory(query)

            # ── Communication ──────────────────────────────────────────────
            elif tool_name == "send_email":
                entities = {
                    "recipient": tool_args.get("recipient", ""),
                    "body": tool_args.get("body", ""),
                    "subject": tool_args.get("subject", "")
                }
                result = self._email_action.execute(entities)
                return result.get("speech", "Email processed.")

            # ── Reminders & Timers ─────────────────────────────────────────
            elif tool_name == "set_reminder":
                duration = tool_args.get("duration_seconds", 0)
                message = tool_args.get("message", "Timer alert!")
                result = self._reminder_action.execute({
                    "duration": duration,
                    "message": message
                })
                return result.get("speech", "Reminder set.")

            # ── Device Control ─────────────────────────────────────────────
            elif tool_name == "open_application":
                return open_application(tool_args.get("app_name", ""))

            elif tool_name == "take_screenshot":
                return take_screenshot()

            elif tool_name == "type_text":
                return type_text(tool_args.get("text", ""))

            elif tool_name == "press_key":
                return press_key(tool_args.get("key", ""))

            elif tool_name == "system_info":
                return get_system_info(tool_args.get("info_type", "all"))

            # ── Browser Automation ─────────────────────────────────────────
            elif tool_name == "browser_action":
                return browser_action(
                    task=tool_args.get("task", ""),
                    url=tool_args.get("url", None)
                )

            # ── Credentials Vault (Nova 2.1) ───────────────────────────────
            elif tool_name == "manage_credentials":
                from core import vault
                action = tool_args.get("action", "")
                site = tool_args.get("site", "")
                username = tool_args.get("username", "")
                password = tool_args.get("password", "")

                if action == "save":
                    return vault.save_credentials(site, username, password)
                elif action == "delete":
                    return vault.delete_credentials(site)
                elif action == "list":
                    creds = vault.list_credentials()
                    if not creds:
                        return "No credentials stored in local vault."
                    return "Stored credentials:\n" + "\n".join([f"- {c['site']}: {c['username']}" for c in creds])
                else:
                    return f"Invalid credentials vault action: {action}"

            else:
                return f"Unknown tool '{tool_name}'. It may not be implemented yet."

        except Exception as e:
            print(f"[Tool] Error in {tool_name}: {e}", file=sys.stderr)
            return f"Tool '{tool_name}' encountered an error: {str(e)}"

    # ── Main Public Interface ──────────────────────────────────────────────

    def process_command(self, text: str) -> dict:
        """
        Process a user text/voice command through the LLM brain.
        Returns structured result for the WebSocket server.
        """
        if not text.strip():
            return {
                "query": "",
                "intent": "unknown",
                "confidence": 0.0,
                "speech": "I didn't catch that. Could you repeat?",
                "ui_data": {}
            }

        clean_text = text.strip().lower()
        print(f"\n[Nova] Processing: '{text}'")

        # ── 1. Check Custom Command Registry (Macro Interceptor) ──────────
        custom_commands = settings.custom_commands
        matched_trigger = None
        for trigger in custom_commands.keys():
            if trigger.strip().lower() in clean_text:
                matched_trigger = trigger
                break

        if matched_trigger:
            print(f"[Assistant] Custom Command Trigger matched: '{matched_trigger}'")
            command_data = custom_commands[matched_trigger]
            
            # Emit status changes and run the actions
            self._push("status_change", {"status": "processing", "text": f"Running macro: {matched_trigger}"})
            self._on_activity("thinking", f"⚡ Executing custom macro: '{matched_trigger}'")
            
            tools_used = []
            thinking_steps = []
            response_text = ""

            if isinstance(command_data, str):
                response_text = command_data
            elif isinstance(command_data, dict):
                # Single action execution
                action_name = command_data.get("action")
                tool_args = {k: v for k, v in command_data.items() if k != "action"}
                
                # Normalize action name to fit standard tools
                if action_name == "search" and "query" in tool_args:
                    action_name = "browser_action"
                    tool_args = {"task": f"Go to {tool_args['query']}"}
                
                tools_used.append(action_name)
                self._on_activity("tool_call", f"⚙️ Running {action_name}...")
                thinking_steps.append({"type": "tool_call", "tool": action_name, "text": f"Running {action_name}"})
                
                tool_result = self._execute_tool(action_name, tool_args)
                
                self._on_activity("tool_result", f"✅ Step completed: {tool_result}")
                thinking_steps.append({"type": "tool_result", "text": f"Completed: {tool_result}"})
                response_text = f"Custom command '{matched_trigger}' executed."
            elif isinstance(command_data, list):
                # Multi-step macro execution
                for idx, step in enumerate(command_data, 1):
                    action_name = step.get("action")
                    tool_args = {k: v for k, v in step.items() if k != "action"}
                    
                    # Normalize action name
                    if action_name == "search" and "query" in tool_args:
                        action_name = "browser_action"
                        tool_args = {"task": f"Go to {tool_args['query']}"}
                    
                    tools_used.append(action_name)
                    self._on_activity("tool_call", f"⚙️ Step {idx}: Running {action_name}...")
                    thinking_steps.append({"type": "tool_call", "tool": action_name, "text": f"Step {idx}: Running {action_name}"})
                    
                    tool_result = self._execute_tool(action_name, tool_args)
                    
                    self._on_activity("tool_result", f"✅ Step {idx} completed: {tool_result}")
                    thinking_steps.append({"type": "tool_result", "text": f"Step {idx} completed"})
                
                response_text = f"Successfully executed macro '{matched_trigger}' with {len(command_data)} steps."

            # Save interaction to episodic memory
            memory_manager.save_interaction(
                user_message=text,
                assistant_response=response_text,
                tools_used=tools_used
            )

            # Speak and return response
            self._push("status_change", {"status": "speaking", "text": response_text})
            audio.speak(response_text)
            self._push("status_change", {"status": "idle", "text": ""})

            return {
                "query": text,
                "intent": "custom_macro",
                "confidence": 1.0,
                "speech": response_text,
                "ui_data": {
                    "tools_used": tools_used,
                    "thinking_steps": thinking_steps,
                    "memory_stats": memory_manager.get_stats()
                }
            }

        # ── 1.5 Fast-Path Direct Launcher (Ultra-Fast < 5ms) ───
        import re
        import webbrowser
        from actions.device_control import APP_MAP

        target_app = None
        open_app_match = re.match(
            r"^(?:please\s+)?(?:can\s+you\s+)?(?:open|launch|run|start|open\s+up|go\s+to|visit)\s+(.+?)(?:\s+please|\s+for\s+me)?$",
            clean_text
        )

        if open_app_match:
            target_app = open_app_match.group(1).strip()
        elif clean_text in APP_MAP or any(k == clean_text for k in APP_MAP):
            target_app = clean_text

        if target_app and target_app not in ("question", "discussion", "ended"):
            print(f"[FastPath] Instant launcher triggered for: '{target_app}'")
            self._push("status_change", {"status": "processing", "text": f"Launching {target_app}..."})
            self._on_activity("tool_call", f"⚡ Instant Launch: '{target_app}'")
            
            res_msg = open_application(target_app)
            speech_res = f"Opened {target_app}."
            
            self._push("status_change", {"status": "speaking", "text": speech_res})
            audio.speak(speech_res)
            self._push("status_change", {"status": "idle", "text": ""})

            return {
                "query": text,
                "intent": "open_application",
                "confidence": 1.0,
                "speech": speech_res,
                "ui_data": {
                    "tools_used": ["open_application"],
                    "thinking_steps": [{"type": "tool_call", "text": f"⚡ Fast-Path: Launched {target_app}"}],
                    "memory_stats": memory_manager.get_stats()
                }
            }

        # ── 1.6 Fast-Path Weather Interceptor (Sub-Second < 100ms) ────────
        weather_match = re.match(
            r"^(?:what(?:'s|\s+is)\s+the\s+)?weather\s+(?:in|of|for|at)\s+(.+?)(?:\s+today|\s+now)?$",
            clean_text
        ) or re.match(
            r"^(.+?)\s+weather$",
            clean_text
        )

        if weather_match:
            city_target = weather_match.group(1).strip()
            print(f"[FastPath] Instant weather triggered for: '{city_target}'")
            self._push("status_change", {"status": "processing", "text": f"Getting weather for {city_target}..."})
            self._on_activity("tool_call", f"🌤️ Instant Weather: '{city_target}'")
            
            weather_res = self._execute_tool("get_weather", {"city": city_target})
            
            self._push("status_change", {"status": "speaking", "text": weather_res})
            audio.speak(weather_res)
            self._push("status_change", {"status": "idle", "text": ""})

            return {
                "query": text,
                "intent": "get_weather",
                "confidence": 1.0,
                "speech": weather_res,
                "ui_data": {
                    "tools_used": ["get_weather"],
                    "thinking_steps": [{"type": "tool_call", "text": f"⚡ Fast-Path: Weather for {city_target}"}],
                    "memory_stats": memory_manager.get_stats()
                }
            }

        # ── 2. Fallback to Groq LLM Brain (Ultra-Fast 8B Instant) ─────────
        # Notify UI that processing started
        self._push("status_change", {"status": "processing", "text": "Thinking..."})

        brain_result = self.brain.think(text)
        response_text = brain_result["response"]
        tools_used = brain_result["tools_used"]
        thinking_steps = brain_result["thinking_steps"]

        # ── Save to persistent memory ──────────────────────────────────────
        memory_manager.save_interaction(
            user_message=text,
            assistant_response=response_text,
            tools_used=tools_used
        )

        # ── Speak the response ─────────────────────────────────────────────
        self._push("status_change", {"status": "speaking", "text": response_text})
        audio.speak(response_text)
        self._push("status_change", {"status": "idle", "text": ""})

        # ── Build result payload ───────────────────────────────────────────
        memory_stats = memory_manager.get_stats()

        return {
            "query": text,
            "intent": tools_used[0] if tools_used else "conversation",
            "confidence": 1.0,
            "speech": response_text,
            "ui_data": {
                "tools_used": tools_used,
                "thinking_steps": thinking_steps,
                "memory_stats": memory_stats
            }
        }

    def clear_session(self):
        """Reset the current conversation context (but keep long-term memory)."""
        self.brain.clear_session()
        return "Session cleared. Long-term memory is preserved."
