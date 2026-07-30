# Nova: Advanced Voice Assistant

Nova is a local-first, privacy-focused voice assistant built with Python. It features a modern, responsive Glassmorphic Web UI dashboard, real-time audio visualizer waveforms, natural language understanding (NLU), and background action controllers (weather, reminders, simulated emails, browser searches, and Wikipedia search).

This project has been developed to adhere to the highest standards of professional Python software engineering—completely clean, modular, and optimized for internship demonstration.

---

## 🌟 Key Features

* **Advanced Glassmorphism UI**: A dark-themed Single Page Application (SPA) dashboard styled with modern typography, glass panels, a central breathing interactive microphone orb, and visual audio visualizer waveforms matching the assistant's state.
* **Hybrid Natural Language Understanding (NLU)**:
  * Uses a vector space model (Cosine Similarity of Term Frequency vectors) to classify free-form user intents with confidence metrics.
  * Employs structured Regex rules for slot/entity extraction (e.g. parsing email addresses, locations, and time durations).
* **Dual-Alert Reminders**: Set time-based reminders (e.g. *"remind me in five seconds to take a break"*). When the countdown ends, a thread triggers a local system tone (`winsound`) and fires a WebSocket event to show a browser-level alert dialog and play synthesized audio.
* **Simulated Outbox & SMTP Live Emailing**: Sends voice-drafted emails. By default, it runs in **Debug Mode**, saving MIME-formatted emails locally inside the `data/outbox/` directory. Live transmission is supported if SMTP credentials are provided in `.env`.
* **Wikipedia General Knowledge QA**: Uses a local client query engine to fetch concise two-sentence factual summaries on general topics (e.g. *"who is Alan Turing"*).
* **Dynamic Settings Panel**: Manage weather API keys, SMTP credentials, voice pitch speed, and customize voice commands dynamically from the interface, saving changes persistently to the local environment configuration.

---

## 📂 Folder Structure

The project follows domain-driven clean packaging:

```
d:/oasis_internship/
├── config/
│   ├── __init__.py
│   ├── settings.py           # Configuration manager (.env and runtime configurations)
│   └── commands.json         # Storage for custom user voice commands
├── core/
│   ├── __init__.py
│   ├── assistant.py          # Main coordinator coordinating TTS, STT, and NLU
│   ├── audio.py              # Pyttsx3 TTS engine and SpeechRecognition wrapper
│   └── nlu.py                # Local Natural Language Understanding (intent & entity parser)
├── actions/
│   ├── __init__.py
│   ├── base.py               # Base class for all voice actions
│   ├── weather.py            # Live weather fetcher using OpenWeatherMap API
│   ├── email_sender.py       # Email simulation and SMTP mail sender
│   ├── search.py             # Web search trigger (opens browser)
│   ├── reminder.py           # Threaded timer with alerts and callback notification
│   └── knowledge.py          # General knowledge search using Wikipedia API
├── gui/
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css     # Premium UI theme (Glassmorphism, dark mode, audio waves)
│   │   ├── js/
│   │   │   └── app.js        # WebSocket messaging and dynamic UI rendering
│   │   └── assets/           # Supporting assets directory
│   ├── templates/
│   │   └── index.html        # Single Page Application frontend
│   ├── __init__.py
│   └── server.py             # FastAPI WebSocket application hosting the UI
├── tests/
│   ├── __init__.py
│   ├── test_nlu.py           # NLU intent parser unit tests
│   └── test_actions.py       # Actions logic unit tests
├── main.py                   # Entry point (launches FastAPI app and logs server)
├── requirements.txt          # Python dependencies
├── .env                      # Local environment configurations (auto-created)
├── .env.example              # Template for environment configurations
└── README.md                 # Detailed documentation and privacy disclosures
```

---

## 🔒 Privacy Considerations & Data Processing Disclosure

In compliance with local-first, privacy-focused design principles, this project processes data according to the following strict guidelines:

1. **Local Audio Capturing (Speech-to-Text)**:
   * **Activation**: The microphone is only opened and captured when you explicitly trigger it (either by clicking the central orb or pressing the Spacebar). No passive or "wake-word" background listening is performed, ensuring zero passive recording.
   * **Transcription**: Audio capture is converted to text using Google's free-tier Web Speech API (via the `speech_recognition` library). A temporary audio clip is sent over HTTPS to Google's transcription endpoint. No voice profiles or identifier metrics are transmitted.
2. **Offline Natural Language Understanding (NLU)**:
   * All voice transcriptions are processed and parsed for intents and entities **100% offline** on your local machine using standard math algorithms (Cosine Similarity) and regular expressions.
3. **Local Storage and Logs**:
   * **Custom Commands**: Custom trigger phrases and replies are stored locally in `config/commands.json`.
   * **Simulated Outbox**: All emails composed in Debug Mode (default) are written purely as `.txt` files in the local directory `data/outbox/` and are never uploaded.
   * **Configuration Persistence**: The API keys and SMTP credentials are stored locally in your private `.env` file on your storage system. No analytics or external tracking trackers are compiled.
4. **Third-Party Live APIs**:
   * **Wikipedia**: Search inquiries for general knowledge questions are sent anonymously to Wikipedia's open query engine.
   * **Weather**: Location lookup queries are queried against OpenWeatherMap. No personal locations are tracked; only the requested city is sent.

---

## ⚙️ Installation & Setup

1. **Verify Requirements**:
   Ensure you are running **Python 3.9** or higher on your system.

2. **Install Dependencies**:
   Execute the pip installer using the requirements template:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: PyAudio relies on C-headers for recording. On Windows, pre-compiled wheels are automatically retrieved. On Linux, you may need `sudo apt-get install portaudio19-dev` before running pip.*

3. **Running the Application**:
   Simply execute the launch script from the project root:
   ```bash
   python main.py
   ```
   This will boot the FastAPI server on `http://127.0.0.1:8000` and automatically open your default browser to show the assistant interface.

4. **Running Unit Tests**:
   Run the pytest suite to verify NLU and actions:
   ```bash
   pytest
   ```
