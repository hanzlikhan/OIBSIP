import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Resolve paths relative to project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")

class Settings:
    # Directories
    DATA_DIR = BASE_DIR / "data"
    OUTBOX_DIR = DATA_DIR / "outbox"
    CONFIG_DIR = BASE_DIR / "config"
    COMMANDS_FILE = CONFIG_DIR / "commands.json"
    VAULT_DIR = Path(os.getenv("NOVA_VAULT_DIR", str(Path.home() / ".nova")))

    # API Keys & Credentials
    WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

    # Nova LLM Settings
    NOVA_LLM_MODEL = os.getenv("NOVA_LLM_MODEL", "llama-3.1-8b-instant")
    NOVA_MAX_TOKENS = int(os.getenv("NOVA_MAX_TOKENS", "1024"))
    NOVA_TEMPERATURE = float(os.getenv("NOVA_TEMPERATURE", "0.7"))

    # SMTP Configuration
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")

    # Debug settings
    DEBUG_MODE = os.getenv("DEBUG_MODE", "True").lower() in ("true", "1", "yes")

    # Assistant settings
    ASSISTANT_NAME = "Nova"
    DEFAULT_VOICE_RATE = 175  # Words per minute
    DEFAULT_VOICE_GENDER = 0  # 0 for male, 1 for female (depends on system voices)

    def __init__(self):
        # Create directories if they do not exist
        self.DATA_DIR.mkdir(exist_ok=True)
        self.OUTBOX_DIR.mkdir(exist_ok=True)
        self.custom_commands = self._load_custom_commands()

    def _load_custom_commands(self) -> dict:
        """Loads custom commands from config/commands.json"""
        if self.COMMANDS_FILE.exists():
            try:
                with open(self.COMMANDS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading custom commands file: {e}")
                return {}
        return {}

    def save_custom_command(self, trigger: str, response_or_action) -> bool:
        """Saves a new custom command both to local state and commands.json"""
        trigger_clean = trigger.strip().lower()
        
        # Try to parse response_or_action as JSON if it looks like a JSON block
        parsed_val = response_or_action
        if isinstance(response_or_action, str) and (response_or_action.strip().startswith("{") or response_or_action.strip().startswith("[")):
            try:
                parsed_val = json.loads(response_or_action)
            except Exception:
                pass
                
        self.custom_commands[trigger_clean] = parsed_val
        try:
            self.CONFIG_DIR.mkdir(exist_ok=True)
            with open(self.COMMANDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.custom_commands, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving custom command: {e}")
            return False

    def delete_custom_command(self, trigger: str) -> bool:
        """Deletes a custom command from local state and commands.json"""
        trigger_clean = trigger.strip().lower()
        if trigger_clean in self.custom_commands:
            del self.custom_commands[trigger_clean]
            try:
                with open(self.COMMANDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.custom_commands, f, indent=2)
                return True
            except Exception as e:
                print(f"Error deleting custom command: {e}")
                return False
        return False

# Global settings instance
settings = Settings()
