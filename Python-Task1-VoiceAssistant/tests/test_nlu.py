"""
Unit tests for the NLU module (Intent parser and slot extraction).
"""

import pytest
from core.nlu import (
    NLUParser, tokenize, INTENT_GREETING, INTENT_TIME, INTENT_SEARCH,
    INTENT_EMAIL, INTENT_REMINDER, INTENT_WEATHER, INTENT_KNOWLEDGE, INTENT_CUSTOM
)

@pytest.fixture
def parser():
    # Simple callback for mock custom commands
    def mock_commands():
        return {
            "tell me a riddle": "What has hands but cannot clap?",
            "open visual studio": {"action": "search", "query": "https://code.visualstudio.com"}
        }
    return NLUParser(custom_commands_callback=mock_commands)

def test_tokenize():
    text = "Hello! Send an email to boss@corp.com, okay?"
    tokens = tokenize(text)
    assert tokens == ["hello", "send", "an", "email", "to", "boss@corp.com", "okay"]

def test_greeting_intent(parser):
    result = parser.parse("hello there assistant")
    assert result["intent"] == INTENT_GREETING
    assert result["confidence"] > 0.3

def test_time_intent(parser):
    result = parser.parse("can you tell me what time it is?")
    assert result["intent"] == INTENT_TIME

def test_search_intent_and_slot(parser):
    result = parser.parse("search the web for cleaner python code")
    assert result["intent"] == INTENT_SEARCH
    assert result["entities"]["query"] == "cleaner python code"

def test_email_intent_and_slots(parser):
    # Test literal email address and message
    result = parser.parse("send an email to test@domain.com saying hello friend")
    assert result["intent"] == INTENT_EMAIL
    assert result["entities"]["recipient"] == "test@domain.com"
    assert result["entities"]["body"] == "hello friend"

    # Test names-based fallback pattern
    result2 = parser.parse("send email to john saying call me back")
    assert result2["intent"] == INTENT_EMAIL
    assert result2["entities"]["recipient"] == "john"
    assert result2["entities"]["body"] == "call me back"

def test_reminder_intent_and_slots(parser):
    # Test number input
    result = parser.parse("set a reminder for 5 seconds to take a walk")
    assert result["intent"] == INTENT_REMINDER
    assert result["entities"]["duration"] == 5
    assert result["entities"]["message"] == "take a walk"

    # Test written word input
    result2 = parser.parse("remind me in ten minutes to call mom")
    assert result2["intent"] == INTENT_REMINDER
    assert result2["entities"]["duration"] == 600
    assert result2["entities"]["message"] == "call mom"

def test_weather_intent_and_slots(parser):
    result = parser.parse("what is the weather in Tokyo?")
    assert result["intent"] == INTENT_WEATHER
    assert result["entities"]["location"] == "Tokyo"

def test_knowledge_intent_and_slots(parser):
    result = parser.parse("who was Alan Turing?")
    assert result["intent"] == INTENT_KNOWLEDGE
    assert result["entities"]["query"] == "Alan Turing"

def test_custom_command_intent(parser):
    # Text command exact match
    result = parser.parse("tell me a riddle")
    assert result["intent"] == INTENT_CUSTOM
    assert result["entities"]["trigger"] == "tell me a riddle"
    assert result["entities"]["command_data"] == "What has hands but cannot clap?"

    # Text command inside sentence match
    result2 = parser.parse("hey, open visual studio")
    assert result2["intent"] == INTENT_CUSTOM
    assert result2["entities"]["trigger"] == "open visual studio"
    assert result2["entities"]["command_data"]["action"] == "search"
