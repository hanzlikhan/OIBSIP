# 📚 Nova Voice Assistant — Complete Beginner-Friendly Guide & Technical Explanation

> **Welcome!** This document is crafted specifically to help you understand **every single file, line of logic, and architectural concept** in Nova. Even if you are a beginner in programming, reading this guide will allow you to confidently present, explain, and defend this project in front of any interviewer, evaluation panel, or audience!

---

## 🌟 1. Project High-Level Summary (The 30-Second Elevator Pitch)

> *"Nova is an autonomous, local-first, privacy-focused AI Voice Assistant built with Python, FastAPI, and Groq LLM Tool Calling. Unlike basic chatbots that only answer text questions, Nova can physically control your computer (launch apps, take screenshots, check hardware stats), automate web pages using Playwright, send emails, set alarms, and understand voice commands in **English** in sub-second speed."*

---

## 🧬 2. The Human Body Analogy (How Nova Works)

To easily explain Nova to anyone, compare it to a human body:

| Human Part | Nova Component | File Location | Simple Explanation |
| :--- | :--- | :--- | :--- |
| **👂 Ears** | Speech-to-Text (STT) | `core/audio.py` | Listens to your voice via microphone and converts spoken audio into written text accurately in English (`en-US`). |
| **🧠 Brain** | Groq LLM Engine & Fast-Path | `core/brain.py` & `core/assistant.py` | Analyzes your request, understands your intent, and decides whether to speak back or run a tool. |
| **🗣️ Voice** | Text-to-Speech (TTS) | `core/audio.py` | Uses Windows SAPI5 voice engine (`pyttsx3`) to speak responses out loud in a non-blocking background thread. |
| **🖐️ Hands** | OS & Web Action Tools | `actions/` directory | Launches apps (Chrome, Notepad), takes screenshots, reads CPU/RAM stats, and automates websites. |
| **🖥️ Face** | Glassmorphic Dashboard UI | `gui/` directory | Modern web page with a pulsing mic orb, dynamic audio visualizer waveforms, and real-time chat log. |
| **🔐 Safe** | Credentials Vault | `core/vault.py` | Protects passwords and API keys using AES-256 encryption. |

---

## 🔄 3. Step-by-Step Journey of a Voice Command

Let's trace what happens step-by-step when you say: **"Chrome kholo"** or **"What is quantum computing?"**

```text
[User Speaks / Types] 
       │
       ▼
1. Web Dashboard (gui/templates/index.html & gui/static/js/app.js)
   - Mic orb clicks or text is entered.
   - App sends a WebSocket event to the server over ws://127.0.0.1:8000/ws.
       │
       ▼
2. FastAPI WebSocket Server (gui/server.py)
   - Receives the message instantly without reloading the page.
   - Relays voice audio to core/audio.py or text directly to core/assistant.py.
       │
       ▼
3. Master Assistant Orchestrator (core/assistant.py)
   - Checks Fast-Path Router (< 5ms): If command is "chrome kholo" or "open notepad",
     it immediately executes OS launch without waiting for network AI!
   - If it's a general question, it routes to Groq LLM (core/brain.py).
       │
       ▼
4. Groq LLM Brain (core/brain.py)
   - Uses ultra-fast `llama-3.1-8b-instant` model.
   - Evaluates whether to answer directly or call a tool (e.g. web_search, get_weather).
       │
       ▼
5. Action Execution (actions/)
   - Runs the tool (e.g., launches Chrome, fetches weather, or searches DuckDuckGo).
   - Writes action details to local audit log (`data/action_log.jsonl`).
       │
       ▼
6. Response & Speech Output (core/audio.py & gui/static/js/app.js)
   - Sends text response to Frontend over WebSockets (updates UI & visualizer waves).
   - Speaks response out loud via pyttsx3 in an isolated non-blocking thread.
```

---

## 📂 4. Detailed File-by-File Breakdown

Here is what every file in your project does, explained in plain English:

### 🟢 **Root Files**

#### 1. `main.py` — *The Application Launcher*
* **What it does**: The main entry point of the application.
* **How it works**:
  - Initializes Python runtime checks.
  - Boots the **FastAPI web server** on `http://127.0.0.1:8000`.
  - Automatically launches your default web browser (Chrome/Edge) to open the dashboard interface.

#### 2. `requirements.txt` — *The Dependency List*
* **What it does**: Lists all external Python libraries needed for Nova (e.g., `fastapi`, `uvicorn`, `groq`, `pyautogui`, `psutil`, `playwright`, `speech_recognition`, `pyttsx3`, `cryptography`).

#### 3. `.env` & `.env.example` — *Environment Credentials*
* **What it does**: Stores private configuration keys (Groq API Key, OpenWeatherMap API Key, SMTP email credentials) safely so they are never hardcoded in source code.

---

### 🔵 **Core Engine (`core/`)**

#### 4. `core/assistant.py` — *The Master Director*
* **What it does**: The central controller that connects the AI brain, action tools, memory, and WebSocket UI.
* **Key Features**:
  - **Fast-Path Router**: Matches instant triggers like *"open chrome"*, *"open notepad"* and executes them in **< 5 milliseconds**!
  - **Tool Routing**: Connects LLM tool requests to actual Python execution functions in `actions/`.

#### 5. `core/brain.py` — *The Groq AI Reasoner*
* **What it does**: Connects to the Groq cloud LLM API using the `llama-3.1-8b-instant` model.
* **Key Features**:
  - **Autonomous Tool Calling**: Declares tools (`web_search`, `device_control`, `set_reminder`, `get_weather`) to the LLM so it can choose which tool to invoke.
  - **English Speech Intelligence**: Instructs the LLM via System Prompt to natively understand English queries and reply naturally.

#### 6. `core/audio.py` — *The Ears & Spoken Voice*
* **What it does**: Manages microphone recording (STT) and text-to-speech voice generation (TTS).
* **Key Features**:
  - **Accurate English STT**: Uses Google Speech Recognition configured for **English (`en-US`)** capture.
  - **Natural Speaking Thresholds**: Set `pause_threshold = 2.0s` (allows 2 seconds mid-sentence pauses without cutting off) and `phrase_time_limit = 25.0s`.
  - **Non-Blocking TTS**: Runs `pyttsx3` inside a daemon thread with `pythoncom.CoInitialize()` so speech never freezes the web UI.

#### 7. `core/vault.py` — *AES-256 Encrypted Safe*
* **What it does**: Encrypts and decrypts sensitive passwords and credentials stored locally in `data/vault.json` using **AES-256 Fernet symmetric encryption**.

#### 8. `core/memory.py` — *The Episodic Memory Engine*
* **What it does**: Saves interaction history (user queries, assistant replies, tools used) into a local SQLite database (`data/nova_memory.db`) so Nova remembers past conversations.

---

### 🟡 **Action Tools (`actions/`)**

#### 9. `actions/device_control.py` — *System & Desktop Automation*
* **What it does**: Controls Windows operating system features using `pyautogui` and `psutil`.
* **Features**:
  - **App Launcher**: Instant launch for Notepad, Calculator, Chrome, VS Code, Task Manager, Settings, Spotify, etc.
  - **Hardware Monitor**: Returns real-time CPU %, free RAM %, disk space, and battery status.
  - **Screenshot Taker**: Saves instant PNG desktop screenshots to `data/screenshots/`.
  - **Safety Failsafe**: `pyautogui.FAILSAFE = True` stops mouse automation if dragged to screen corners.

#### 10. `actions/browser_automation.py` — *Playwright Web Automator*
* **What it does**: Uses **Playwright** browser engine to open web pages, fill out form inputs, click buttons, and extract live web data.

#### 11. `actions/web_search.py` — *Internet Search Engine*
* **What it does**: Queries DuckDuckGo for live internet search results and extracts clean web article content without requiring paid API keys.

#### 12. `actions/weather.py` — *Weather Forecast Fetcher*
* **What it does**: Queries OpenWeatherMap API for live temperature, humidity, and atmospheric conditions for any city worldwide.

#### 13. `actions/reminder.py` — *Threaded Alarm Clock*
* **What it does**: Launches asynchronous background timer threads. When the countdown expires, it triggers system audio beeps (`winsound`) and sends a WebSocket alert modal to the UI.

#### 14. `actions/email_sender.py` — *Email Outbox & SMTP Transmitter*
* **What it does**: Features a dual-mode email pipeline:
  - **Debug Mode (Default)**: Saves voice-drafted MIME emails locally as `.txt` files in `data/outbox/`.
  - **Production Mode**: Sends live emails over SMTP (`smtp.gmail.com`).

---

### 🟣 **User Interface (`gui/`)**

#### 15. `gui/server.py` — *FastAPI WebSocket Bridge*
* **What it does**: Hosts the web server and manages bi-directional WebSocket client connections (`ws://127.0.0.1:8000/ws`).

#### 16. `gui/templates/index.html` — *Dashboard SPA HTML Structure*
* **What it does**: Single Page Application structure containing the central breathing mic orb, activity log tab, settings panel, and alarm modals.

#### 17. `gui/static/css/style.css` — *Glassmorphic Visual Design*
* **What it does**: Modern CSS design system featuring dark mode, glass blur panels (`backdrop-filter`), vibrant color tokens, and glowing orb animations.

#### 18. `gui/static/js/app.js` — *Frontend Interactivity & WebSockets*
* **What it does**: Handles mic orb click events, spacebar hotkey triggers, dynamic Canvas audio waveform animations, and WebSocket event payloads.

---

## 🎯 5. How to Present/Defend This Project (Interview Cheatsheet)

When presenting this project, use these key talking points:

### 1. **"How does Nova achieve sub-second fast performance?"**
> *"We optimized speed on three levels: First, we use Groq's high-speed `llama-3.1-8b-instant` LLM model for 100ms reasoning. Second, we built a Fast-Path Router that intercepts common app and browser commands like 'open chrome' in under 5 milliseconds. Third, speech synthesis runs asynchronously in background daemon threads so the UI never waits for audio playback."*

### 2. **"How does English Speech Recognition work?"**
> *"We implemented focused English speech recognition in `core/audio.py` using `en-US` Google STT to ensure maximum accuracy without acoustic overlap or hallucinations."*

### 3. **"How does Nova protect user privacy?"**
> *"Nova is local-first. The microphone is strictly closed by default and only activates on explicit user triggers (zero background listening). Sensitive credentials are encrypted with AES-256 Fernet keys in `core/vault.py`, and all automated actions leave a transparent audit log in `data/action_log.jsonl`."*

---

## 🛠️ 6. Key Technologies Summary

| Technology | Role in Nova |
| :--- | :--- |
| **Python 3.9+** | Core programming language |
| **FastAPI & Uvicorn** | High-performance asynchronous web server framework |
| **WebSockets** | Low-latency bi-directional messaging between Python backend and browser UI |
| **Groq API (`llama-3.1-8b-instant`)** | High-reasoning LLM engine for autonomous tool calling |
| **PyAutoGUI & psutil** | Native OS desktop automation & hardware metrics monitoring |
| **Playwright** | Headless/headful browser automation engine |
| **pyttsx3 & SAPI5** | Local offline Text-to-Speech synthesis |
| **SpeechRecognition** | Microphone capture & Google Speech-to-Text translation |
| **Cryptography (Fernet)** | AES-256 symmetric encryption for credentials storage |
| **HTML5 / CSS3 / JavaScript** | Glassmorphic Single Page Application (SPA) frontend |

---

> 💡 *Keep this document as your master study guide whenever you need to demonstrate or explain Nova!*
