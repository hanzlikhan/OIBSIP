"""
Audio Module.
Handles Speech-to-Text (STT) using SpeechRecognition and Text-to-Speech (TTS) using Pyttsx3.
Safe to use inside multi-threaded contexts (like FastAPI/WebSockets).
"""

import sys
import threading
import speech_recognition as sr
from config.settings import settings

_thread_local = threading.local()

def _get_tts_engine():
    """Lazily initialize and cache the pyttsx3 engine per-thread."""
    if not hasattr(_thread_local, "engine"):
        import pyttsx3
        _thread_local.engine = pyttsx3.init()
    return _thread_local.engine

# Thread-safe non-blocking TTS function. Uses SAPI5 on Windows safely.
def speak(text: str, rate: int = None, gender: int = None) -> bool:
    """
    Speaks the given text using local TTS engine.
    Runs asynchronously in a background thread so it never blocks the server or WebSocket loop.
    """
    if not text or not text.strip():
        return True

    voice_rate = rate if rate is not None else settings.DEFAULT_VOICE_RATE
    voice_gender = gender if gender is not None else settings.DEFAULT_VOICE_GENDER

    def _speak_worker():
        try:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass

            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", voice_rate)
            
            voices = engine.getProperty("voices")
            if voices:
                index = min(max(0, voice_gender), len(voices) - 1)
                engine.setProperty("voice", voices[index].id)
                
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS Execution Warning] {e}", file=sys.stderr)

    t = threading.Thread(target=_speak_worker, daemon=True)
    t.start()
    return True

class STTManager:
    """Manages recording voice and returning text transcription."""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # High-sensitivity dynamics for complete voice capture without premature cutoffs
        self.recognizer.energy_threshold = 250
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 2.0  # 2.0 seconds pause allowed mid-sentence without cutting off
        self.recognizer.non_speaking_duration = 1.0
        self.microphone = None
        self._adjusted = False

    def _get_microphone(self) -> sr.Microphone:
        """Lazily initialize and cache the Microphone instance."""
        if self.microphone is None:
            self.microphone = sr.Microphone()
        return self.microphone

    def listen_and_transcribe(self, timeout: float = 10.0, phrase_time_limit: float = 25.0) -> dict:
        """
        Listens on the system microphone and returns a dictionary with transcription or error messages.
        
        Returns:
            dict: {
                "success": bool,
                "text": str,
                "error_code": str ("timeout", "unknown_value", "service_error", "no_mic")
            }
        """
        # Ensure we have active audio capture hardware
        try:
            mic = self._get_microphone()
        except OSError as e:
            print(f"Microphone access error: {e}", file=sys.stderr)
            return {
                "success": False,
                "text": "",
                "error_code": "no_mic"
            }

        try:
            with mic as source:
                if not self._adjusted:
                    print("Adjusting microphone for ambient noise (quick)...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    self._adjusted = True
                
                print(f"Listening (timeout={timeout}s, phrase_limit={phrase_time_limit}s)...")
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
                
            print("Processing voice audio...")
            # Use Google Web Speech API (free tier built-in)
            transcription = self.recognizer.recognize_google(audio)
            return {
                "success": True,
                "text": transcription,
                "error_code": ""
            }
            
        except sr.WaitTimeoutError:
            return {
                "success": False,
                "text": "",
                "error_code": "timeout"
            }
        except sr.UnknownValueError:
            return {
                "success": False,
                "text": "",
                "error_code": "unknown_value"
            }
        except sr.RequestError as e:
            print(f"Google Speech Recognition Service Error: {e}", file=sys.stderr)
            return {
                "success": False,
                "text": "",
                "error_code": "service_error"
            }
        except Exception as e:
            print(f"Audio transcription unexpected error: {e}", file=sys.stderr)
            return {
                "success": False,
                "text": "",
                "error_code": "service_error"
            }
