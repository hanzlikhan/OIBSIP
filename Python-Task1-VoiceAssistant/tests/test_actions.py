"""
Unit tests for the individual Voice Assistant action modules.
"""

import os
import shutil
import pytest
from pathlib import Path
from config.settings import settings
from actions.search import SearchAction
from actions.email_sender import EmailSenderAction
from actions.weather import WeatherAction
from actions.reminder import ReminderAction

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Initializes clean directory configurations before each test."""
    # Override settings directories to use temp test paths
    original_data_dir = settings.DATA_DIR
    original_outbox_dir = settings.OUTBOX_DIR
    
    test_data = Path(__file__).resolve().parent / "test_data"
    test_outbox = test_data / "outbox"
    
    settings.DATA_DIR = test_data
    settings.OUTBOX_DIR = test_outbox
    
    test_outbox.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Tear down
    if test_data.exists():
        shutil.rmtree(test_data)
        
    settings.DATA_DIR = original_data_dir
    settings.OUTBOX_DIR = original_outbox_dir

def test_search_action_query():
    action = SearchAction()
    # Mock webbrowser.open to check execution path
    import webbrowser
    original_open = webbrowser.open
    opened_urls = []
    webbrowser.open = lambda url: opened_urls.append(url)
    
    # Check general search query
    res = action.execute({"query": "python decorators"})
    assert "Searching the web" in res["speech"]
    assert len(opened_urls) == 1
    assert "google.com/search" in opened_urls[0]
    
    # Check website address query
    res2 = action.execute({"query": "github.com"})
    assert "Opening website" in res2["speech"]
    assert len(opened_urls) == 2
    assert opened_urls[1] == "https://github.com"
    
    webbrowser.open = original_open

def test_email_sender_action_simulation():
    action = EmailSenderAction()
    
    # Force settings into debug mode
    settings.DEBUG_MODE = True
    
    entities = {
        "recipient": "friend@example.com",
        "body": "This is a unit test message."
    }
    
    res = action.execute(entities)
    assert res["ui_data"]["status"] == "simulated"
    assert "simulated sending the email" in res["speech"]
    
    # Verify that the outbox file was written
    outbox_files = list(settings.OUTBOX_DIR.glob("*.txt"))
    assert len(outbox_files) == 1
    
    with open(outbox_files[0], "r", encoding="utf-8") as f:
        content = f.read()
        assert "To: friend@example.com" in content
        assert "Body:\nThis is a unit test message." in content

def test_weather_action_simulation():
    action = WeatherAction()
    
    # Force settings into empty weather key state to trigger simulation
    settings.WEATHER_API_KEY = ""
    
    res = action.execute({"location": "Berlin"})
    assert res["ui_data"]["status"] == "simulated"
    assert res["ui_data"]["location"] == "Berlin"
    assert isinstance(res["ui_data"]["temp"], int)
    assert "Berlin" in res["speech"]
    assert "Simulating" in res["speech"]

def test_reminder_action_setup():
    # Mock winsound.Beep if it exists to prevent test audio delays
    original_beep = None
    try:
        import winsound
        original_beep = winsound.Beep
        winsound.Beep = lambda f, d: None
    except ImportError:
        pass

    try:
        # Pass a dummy callback to check trigger behavior
        triggered = []
        def dummy_callback(rem_id, msg):
            triggered.append((rem_id, msg))
            
        action = ReminderAction(ws_callback=dummy_callback)
        
        # Set a tiny 1-second timer to avoid stalling test execution
        res = action.execute({"duration": 1, "message": "wake up"})
        assert res["ui_data"]["message"] == "wake up"
        assert "set a reminder" in res["speech"]
        assert "1 second" in res["speech"]
        
        # Wait for execution and verify callback triggers
        import time
        time.sleep(1.2)
        assert len(triggered) == 1
        assert triggered[0][1] == "wake up"
    finally:
        if original_beep:
            import winsound
            winsound.Beep = original_beep
