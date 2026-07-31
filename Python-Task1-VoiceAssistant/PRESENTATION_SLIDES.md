# 🖥️ Oasis Infobyte Internship Presentation Slides

---

## 📌 SLIDE 1: Title Slide (Cover)

```text
================================================================================
                    OASIS INFOBYTE INTERNSHIP PROGRAM (OIBSIP)
================================================================================

                           PROJECT PRESENTATION

       Project Title  : NOVA — Advanced Local-First AI Voice Assistant
       Task Number    : Task 1 (Python Development Track)
       Internship     : Oasis Infobyte Virtual Internship Program (OIBSIP)
       Company        : Oasis Infobyte

       Presented By   : Muhammad Hanzla
       Domain         : Python Development
       Repository     : https://github.com/hanzlikhan/OIBSIP
================================================================================
```

---

## 📌 SLIDE 2: Project Overview & Objective

### 🎯 **Executive Summary**
* **Project Name**: Nova AI Voice Assistant
* **Core Objective**: To build an autonomous, privacy-focused, sub-second voice assistant capable of desktop control, web automation, real-time search, and high-accuracy English voice recognition.

### 💡 **Key Innovations**
* **Local-First & Privacy-Focused**: Zero background microphone listening. Audio is processed on explicit user activation.
* **Autonomous LLM Tool Reasoning**: Powered by Groq `llama-3.1-8b-instant` for ultra-fast function calling.
* **High-Accuracy Speech Intelligence**: Optimized Google STT recognition in **English (`en-US`)**.

---

## 📌 SLIDE 3: Key Features & Capabilities

* 🧠 **Autonomous AI Brain & Tool Calling**:
  * Leverages Groq LLM reasoning to dynamically invoke system actions (`web_search`, `device_control`, `set_reminder`, `get_weather`).
* ⚡ **Sub-Second Fast-Path Launcher (< 5ms)**:
  * Instantly opens applications (Chrome, Notepad, Calculator, VS Code) and websites (YouTube, ChatGPT, GitHub).
* 🎙️ **High-Accuracy Voice Recognition**:
  * Precise English Speech Recognition supporting direct voice commands (*"Open Chrome"*, *"What's the weather?"*).
* 💻 **Desktop & Hardware Diagnostics**:
  * Monitors real-time CPU, RAM, disk space, and battery metrics via `psutil`. Captures desktop screenshots via `pyautogui`.
* 🔒 **AES-256 Encrypted Credentials Vault**:
  * Protects local passwords and keys using Fernet symmetric cryptography (`cryptography` library).
* ⏰ **Threaded Alarm & Outbox Email Engine**:
  * Asynchronous timer threads with Web Audio API sound alerts + simulated `.txt` outbox email delivery.

---

## 📌 SLIDE 4: Architecture & Working Pipeline

```text
[ User Voice / Text Input ]
          │
          ▼
[ Single Page Application Dashboard ] ── (HTML5 / CSS3 Glassmorphism / JS)
          │
          ▼  (FastAPI Bi-directional WebSockets: sub-50ms)
[ FastAPI Backend Server ] ── (gui/server.py & core/assistant.py)
          │
     ┌────┴──────────────────────────┐
     ▼                               ▼
[ Fast-Path Router ]       [ Groq LLM Engine ]
(Instant <5ms launch)     (llama-3.1-8b-instant)
     │                               │
     └──────────────┬────────────────┘
                    ▼
          [ Action Execution ] ── (PyAutoGUI / Playwright / DuckDuckGo)
                    │
                    ▼
          [ Audio & UI Response ] ── (Non-blocking SAPI5 TTS / Visualizer Waves)
```

---

## 📌 SLIDE 5: Technology Stack

| Category | Technologies & Tools |
| :--- | :--- |
| **Primary Language** | Python 3.9+ |
| **Backend & WebSockets** | FastAPI, Uvicorn, WebSockets |
| **AI / LLM Engine** | Groq API (`llama-3.1-8b-instant`), Natural Language Processing |
| **Speech Recognition (STT)** | SpeechRecognition (Google Web Speech API: `en-US`) |
| **Speech Synthesis (TTS)** | Pyttsx3 / Microsoft SAPI5 (Non-blocking background thread) |
| **OS & Web Automation** | PyAutoGUI, psutil, Playwright (Headless/Headful Browser) |
| **Security & Database** | Cryptography (`Fernet` AES-256), SQLite (`nova_memory.db`) |
| **Frontend UI** | HTML5, Modern Vanilla CSS3 (Glassmorphism), JavaScript (ES6 Canvas) |

---

## 📌 SLIDE 6: Summary & Submission Details

* **Task Status**: 100% Completed & Verified (14 Unit Tests Passing)
* **GitHub Repository**: [https://github.com/hanzlikhan/OIBSIP](https://github.com/hanzlikhan/OIBSIP)
* **Submission Directory**: `OIBSIP/Python-Task1-VoiceAssistant/`
* **Company**: Oasis Infobyte
* **Program**: Oasis Infobyte Virtual Internship Program (OIBSIP)

---
