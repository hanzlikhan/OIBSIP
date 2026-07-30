"""
Nova Brain — Groq LLM Engine with Tool Calling
The central intelligence of the Nova AI Agent.
Replaces the old cosine similarity NLU with genuine reasoning and autonomous tool use.
"""

import os
import json
import sys
from typing import Any
from groq import Groq
from config.settings import settings

# ─────────────────────────────────────────────────────────────────────────────
# Tool Definitions — These are the "skills" exposed to the LLM
# The LLM reads these descriptions and decides which to call autonomously
# ─────────────────────────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the internet in real-time for any topic, news, facts, prices, "
                "current events, or anything that requires up-to-date information. "
                "Use this for any question you are not 100% certain about."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the web."
                    },
                    "fetch_page": {
                        "type": "boolean",
                        "description": "If true, fetches and reads the full content of the top result for a deep answer."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time_and_date",
            "description": "Get the current local time and date.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a timer or reminder that fires after a specified duration with an audible alert.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_seconds": {
                        "type": "integer",
                        "description": "Duration in seconds before the reminder fires."
                    },
                    "message": {
                        "type": "string",
                        "description": "The reminder message to display and speak when the timer fires."
                    }
                },
                "required": ["duration_seconds", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open or launch any application on the user's computer by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to launch (e.g. 'notepad', 'chrome', 'vs code', 'spotify')."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot of the user's current screen and save it.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": (
                "ONLY use this to physically type text into an EXTERNAL application window on the user's computer "
                "(e.g., Notepad, VS Code, a browser text field). "
                "NEVER use this tool to deliver your own response or reply — just respond with text directly. "
                "Example valid uses: 'Type hello world into Notepad', 'Type my name into the search box'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to physically type into the currently focused external application."
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_action",
            "description": (
                "Control the web browser to visit any website, click buttons, type text, "
                "post on social media (Facebook, Twitter/X, LinkedIn), send WhatsApp messages, "
                "fill forms, or perform any web-based task. Be specific about what to do."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": (
                            "Detailed description of what to do in the browser. Examples: "
                            "'Go to facebook.com and post: Hello everyone!', "
                            "'Open web.whatsapp.com, find contact John, send message: Are you free?', "
                            "'Go to google.com and search for Python tutorials', "
                            "'Open youtube.com and search for relaxing music'"
                        )
                    },
                    "url": {
                        "type": "string",
                        "description": "Optional starting URL to navigate to."
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description": "Get current system information: CPU usage, RAM usage, running processes, disk space.",
            "parameters": {
                "type": "object",
                "properties": {
                    "info_type": {
                        "type": "string",
                        "enum": ["cpu", "ram", "processes", "disk", "all"],
                        "description": "What system information to retrieve."
                    }
                },
                "required": ["info_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather conditions for a specified city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name to get weather for."
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Draft and send or save an email to a recipient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {"type": "string", "description": "Email address or name of the recipient."},
                    "body": {"type": "string", "description": "Body content of the email."},
                    "subject": {"type": "string", "description": "Subject line of the email."}
                },
                "required": ["recipient", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Remember a fact, preference, or piece of information about the user for future sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Short label for this memory (e.g. 'user_name', 'preference_language')."},
                    "value": {"type": "string", "description": "The value to remember."}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Search and retrieve past memories or conversation history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to look up in memory."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_credentials",
            "description": (
                "Save, update, list, or delete credentials (username and password) "
                "for specific websites or apps (e.g. facebook, twitter, gmail) in the secure local vault. "
                "Do NOT call this to login; only call this when the user explicitly requests to save/remember, "
                "list, or delete credentials."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["save", "delete", "list"],
                        "description": "The credential manager action to perform."
                    },
                    "site": {
                        "type": "string",
                        "description": "The site or application name (e.g., 'facebook', 'gmail', 'twitter')."
                    },
                    "username": {
                        "type": "string",
                        "description": "Username, email, or handle to save."
                    },
                    "password": {
                        "type": "string",
                        "description": "Password to save."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a specific keyboard key or combination of keys (e.g. 'enter', 'ctrl+c', 'alt+tab').",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "The key or key combination to press (e.g. 'enter', 'ctrl+c', 'win+r')."
                    }
                },
                "required": ["key"]
            }
        }
    }
]


SYSTEM_PROMPT = """You are Nova — an advanced, intelligent AI assistant running locally on the user's Windows PC.
You are NOT a simple chatbot. You are a proactive AI AGENT with access to powerful tools.

Your Personality:
- Sharp, confident, and helpful. You think before you speak.
- You're honest — if you don't know something, you search the web rather than guess.
- You keep responses concise for voice — no bullet points, no markdown, just natural speech.
- You can handle complex multi-step tasks autonomously.

MULTILINGUAL & URDU LANGUAGE RULES:
- You are 100% fluent in Urdu (اردو), Roman Urdu (e.g. 'kya haal hai', 'chrome kholo', 'mausam kaisa hai'), and English.
- Understand commands spoken in Urdu or Roman Urdu:
  * "chrome kholo" / "کروم کھولو" -> call open_application(app_name="chrome")
  * "mausam kaisa hai" / "موسم کیسا ہے" -> call get_weather(city="...")
  * "waqt kya hua hai" / "وقت کیا ہوا ہے" -> call get_time_and_date()
  * "notepad open karo" / "نوٹ پیڈ کھولو" -> call open_application(app_name="notepad")
- Always reply in the SAME language/script the user used to speak to you. If the user speaks in Urdu or Roman Urdu, reply in natural, friendly Urdu or Roman Urdu.

Your Capabilities:
- Search the internet in real time for any question
- Control the user's computer: open apps, take screenshots, type text into apps
- Automate any website: post on Facebook, send WhatsApp messages, fill forms
- Set reminders and timers
- Remember user preferences and past conversations
- Fetch live weather, system stats, and more

CRITICAL TOOL USAGE RULES — READ CAREFULLY:
1. NEVER call `type_text` to deliver your own reply or response. `type_text` is ONLY for physically typing text into an external app window (like Notepad or VS Code) when the user explicitly asks you to.
2. NEVER use any device control tool (open_application, take_screenshot, type_text, press_key) unless the user explicitly asks you to perform that action on their computer.
3. For greetings, questions, and conversation — respond with PLAIN TEXT directly. Do NOT call any tool.
4. Only call `web_search` when factual, current, or real-time information is genuinely needed. Simple questions you know the answer to (e.g. math, capitals, definitions) do NOT need a web search.
5. Keep spoken responses short and natural — 1-3 sentences for simple answers.
6. When calling multiple tools, chain them logically.
7. If you are about to do something potentially destructive (post publicly, delete files), briefly confirm first.
8. You are running on Windows. Use Windows-compatible app names (e.g., 'notepad.exe', 'chrome.exe').
"""

class NovaBrain:
    """
    Groq-powered LLM brain for the Nova AI Agent.
    Manages conversation history, tool routing, and streaming responses.
    """

    def __init__(self, tool_executor=None, ws_activity_callback=None):
        """
        tool_executor: Callable(tool_name, tool_args) -> str result
        ws_activity_callback: Callable(step_type, message) for live activity feed
        """
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env file.")

        self.client = Groq(api_key=api_key)
        self.model = os.getenv("NOVA_LLM_MODEL", "llama-3.3-70b-versatile")
        self.max_tokens = int(os.getenv("NOVA_MAX_TOKENS", "1024"))
        self.temperature = float(os.getenv("NOVA_TEMPERATURE", "0.7"))
        self.tool_executor = tool_executor
        self.ws_activity_callback = ws_activity_callback

        # In-session conversation history (working memory)
        self.conversation_history: list[dict] = []
        self.max_history_turns = 20  # Keep last 20 turns in context

    def _emit(self, step_type: str, message: str):
        """Push a live activity update to the UI."""
        if self.ws_activity_callback:
            try:
                self.ws_activity_callback(step_type, message)
            except Exception:
                pass

    def _trim_history(self):
        """Keep conversation history within token limits."""
        if len(self.conversation_history) > self.max_history_turns * 2:
            # Keep system context intact, trim oldest pairs
            self.conversation_history = self.conversation_history[-self.max_history_turns * 2:]

    def think(self, user_message: str) -> dict:
        """
        Main reasoning loop.
        Takes user input, runs LLM with tool calling, executes tools,
        and returns the final text response.

        Returns:
            dict: {
                "response": str,          # Final spoken/displayed response
                "tools_used": list[str],  # Which tools were called
                "thinking_steps": list    # Activity log for UI
            }
        """
        tools_used = []
        thinking_steps = []

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        self._trim_history()

        self._emit("thinking", "🧠 Understanding your request...")
        thinking_steps.append({"type": "thinking", "text": "Understanding your request..."})

        # Build message list with system prompt
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.conversation_history

        # ── Tool-calling agentic loop ──────────────────────────────────────
        max_iterations = 5  # Prevent infinite tool loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
            except Exception as e:
                error_str = str(e)

                # ── Auto-retry: tool_use_failed (400) ─────────────────────
                # Groq returns this when the LLM generates a malformed tool call.
                # Retry once without tools (plain text response mode).
                if "tool_use_failed" in error_str or "400" in error_str:
                    print(f"[Brain] tool_use_failed detected, retrying without tools...", file=sys.stderr)
                    try:
                        fallback_response = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            tool_choice="none",   # Force plain text output
                            max_tokens=self.max_tokens,
                            temperature=self.temperature
                        )
                        final_response = fallback_response.choices[0].message.content or "I'm here! How can I help you?"
                        self.conversation_history.append({"role": "assistant", "content": final_response})
                        return {"response": final_response, "tools_used": tools_used, "thinking_steps": thinking_steps}
                    except Exception as retry_e:
                        print(f"[Brain] Fallback retry also failed: {retry_e}", file=sys.stderr)

                error_msg = f"I'm having trouble reaching my AI engine. Please try again in a moment."
                print(f"Groq API error: {e}", file=sys.stderr)
                self.conversation_history.append({"role": "assistant", "content": error_msg})
                return {"response": error_msg, "tools_used": tools_used, "thinking_steps": thinking_steps}


            choice = response.choices[0]
            message = choice.message

            # ── Check if LLM wants to call tools ──────────────────────────
            if choice.finish_reason == "tool_calls" and message.tool_calls:
                # Add the assistant's tool-call intent to message history
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })

                # Execute each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    tools_used.append(tool_name)

                    # ── Emit activity to UI ────────────────────────────────
                    activity_icons = {
                        "web_search": f"🔍 Searching the web for: {tool_args.get('query', '')}",
                        "browser_action": f"🌐 Browser: {tool_args.get('task', '')[:60]}...",
                        "open_application": f"🚀 Opening {tool_args.get('app_name', '')}...",
                        "take_screenshot": "📷 Taking screenshot...",
                        "type_text": f"⌨️ Typing text...",
                        "set_reminder": f"⏰ Setting reminder: {tool_args.get('message', '')}",
                        "system_info": f"💻 Checking system {tool_args.get('info_type', 'info')}...",
                        "get_weather": f"🌤️ Getting weather for {tool_args.get('city', '')}...",
                        "send_email": f"📧 Preparing email to {tool_args.get('recipient', '')}...",
                        "save_memory": f"💾 Remembering: {tool_args.get('key', '')}",
                        "recall_memory": f"🧠 Searching memory for: {tool_args.get('query', '')}...",
                        "get_time_and_date": "🕐 Checking time and date...",
                        "manage_credentials": f"🔐 Vault: {tool_args.get('action', '')} for {tool_args.get('site', 'credentials')}...",
                        "press_key": f"⌨️ Pressing key: {tool_args.get('key', '')}"
                    }
                    activity_msg = activity_icons.get(tool_name, f"⚙️ Running {tool_name}...")
                    self._emit("tool_call", activity_msg)
                    thinking_steps.append({"type": "tool_call", "tool": tool_name, "text": activity_msg})

                    # ── Execute the tool ───────────────────────────────────
                    if self.tool_executor:
                        try:
                            tool_result = self.tool_executor(tool_name, tool_args)
                        except Exception as e:
                            tool_result = f"Error executing {tool_name}: {str(e)}"
                            print(f"Tool execution error ({tool_name}): {e}", file=sys.stderr)
                    else:
                        tool_result = f"Tool {tool_name} is not connected to an executor."

                    # Add tool result back to messages for next LLM turn
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_result)
                    })

                    self._emit("tool_result", f"✅ {tool_name} completed")
                    thinking_steps.append({"type": "tool_result", "text": f"{tool_name} completed"})

                # Continue the loop — LLM will process tool results
                continue

            else:
                # ── LLM produced a final text response ────────────────────
                final_response = message.content or "I completed that task."

                # Add to conversation history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": final_response
                })

                self._emit("response_ready", "💬 Generating response...")
                thinking_steps.append({"type": "response", "text": "Response ready"})

                return {
                    "response": final_response,
                    "tools_used": tools_used,
                    "thinking_steps": thinking_steps
                }

        # Safety: return if max iterations hit
        fallback = "I ran into a complex chain of actions. Please try rephrasing your request."
        self.conversation_history.append({"role": "assistant", "content": fallback})
        return {"response": fallback, "tools_used": tools_used, "thinking_steps": thinking_steps}

    def clear_session(self):
        """Clear working memory / start a fresh conversation."""
        self.conversation_history = []
