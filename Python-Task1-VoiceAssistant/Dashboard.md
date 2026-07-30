# Project Dashboard: Nova AI Agent

## Status Overview
* **Status**: Live & Active (Release 2.1)
* **Main Entry**: [main.py](file:///d:/oasis_internship/main.py)
* **Latest Verification**: Pytest suite passing with 14/14 tests successful (including encrypted vault test suite).

## Features Completed
- **Groq Llama 3.3 70B LLM Brain**: Full tool-calling agentic loop replacing old cosine NLU.
- **Encrypted local credentials vault**: AES-256 Fernet encrypted credential vault stored in `~/.nova/vault.json`.
- **Self-healing browser automation**: Playwright semantic matches (e.g. matching button text) instead of fragile class selectors.
- **Auto-Login integration**: Checks login states on websites, fetches credentials from vault, auto-fills login details instantly.
- **Persistent browser profiles**: Saves cookies and logins to `data/browser_context` so users stay authenticated.
- **Spotlight-style HUD Overlay**: Raycast/macOS Spotlight style popup, summoned globally via `Ctrl + Shift + Space`.
- **Background system tray shortcut**: Background global keyboard hotkey listener thread.
- **Mic Audio capture**: Speech recognition integration configured locally in thread pools.
- **Local TTS feedback**: Thread-safe pyttsx3 vocal response engine.
- **Real-time Web Search**: DuckDuckGo search returning live results with zero API key dependencies.
- **Timer reminders**: Threaded local alarms and overlay UI dimissable alarms.

## Inbox / Needs Action
- None.

## Done / Archive
- `[x]` Release 1.0 (Cosine NLU + base actions)
- `[x]` Release 2.0 (LLM brain + DuckDuckGo + PyAutoGUI + Playwright automation)
- `[x]` Release 2.1 (Encrypted local vault + Auto-login + Global Hotkey + Spotlight HUD)
