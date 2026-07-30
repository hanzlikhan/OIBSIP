"""
Natural Language Understanding (NLU) Module.
Contains the intent classifier and slot/entity extraction algorithms.
Uses a vector space model (Cosine Similarity) and regular expressions.
"""

import re
import math
from collections import Counter

# Intent Categories
INTENT_GREETING = "greeting"
INTENT_TIME = "time"
INTENT_SEARCH = "search"
INTENT_EMAIL = "email"
INTENT_REMINDER = "reminder"
INTENT_WEATHER = "weather"
INTENT_KNOWLEDGE = "knowledge"
INTENT_CUSTOM = "custom"
INTENT_HELP = "help"
INTENT_UNKNOWN = "unknown"

# Reference sentences for each intent (used for Cosine Similarity classification)
TRAINING_DATA = {
    INTENT_GREETING: [
        "hello assistant", "hello", "hi there", "hey", "good morning", "good afternoon", 
        "wake up", "greetings", "is anyone there", "hello server"
    ],
    INTENT_TIME: [
        "what time is it", "tell me the time", "current time", "what is the date today", 
        "current date", "what is the date", "tell me the date", "show me today's date", 
        "what day is it"
    ],
    INTENT_SEARCH: [
        "search the web for python tutorial", "search for clean code", "google standard library", 
        "look up local restaurants", "do a web search for how to cook pasta", "open browser and search for"
    ],
    INTENT_EMAIL: [
        "send an email to test@example.com", "write a mail to buddy", "send email to friend", 
        "mail my manager saying I will be late", "send email with subject hello", "email boss"
    ],
    INTENT_REMINDER: [
        "set a reminder for five minutes", "remind me in ten seconds to take a break", 
        "set a timer for one hour", "start a timer for thirty seconds", "remind me to check the oven in twenty minutes",
        "set a reminder for five seconds"
    ],
    INTENT_WEATHER: [
        "what is the weather like", "weather forecast", "how is the weather in New York", 
        "is it raining today", "forecast in London", "temperature in Paris", "weather today"
    ],
    INTENT_KNOWLEDGE: [
        "who is Alan Turing", "what is an algorithm", "tell me about gravity", 
        "search wikipedia for artificial intelligence", "who was Nikola Tesla", 
        "explain the theory of relativity", "what do you know about space"
    ],
    INTENT_HELP: [
        "help me", "what can you do", "show commands", "list commands", "how do I use you", 
        "give me instructions", "help"
    ]
}

def tokenize(text: str) -> list[str]:
    """Cleans, lowercases, and splits text into alphabetic tokens."""
    text = text.lower()
    # Remove punctuation
    text = re.sub(r"[^\w\s@\.]", "", text)
    return [w for w in text.split() if w]

def text_to_vector(text: str) -> Counter:
    """Converts text string into a Counter vector of word frequencies."""
    return Counter(tokenize(text))

def cosine_similarity(vec1: Counter, vec2: Counter) -> float:
    """Calculates cosine similarity between two frequency vectors."""
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x] ** 2 for x in vec1.keys()])
    sum2 = sum([vec2[x] ** 2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    return float(numerator) / denominator

class NLUParser:
    def __init__(self, custom_commands_callback=None):
        """
        NLU Parser constructor.
        custom_commands_callback: A function that returns a dictionary of custom commands
                                  mapping triggers to responses/actions.
        """
        self.custom_commands_callback = custom_commands_callback

    def parse(self, text: str) -> dict:
        """
        Parses free-form spoken text to extract the intent and entities.
        Returns a dict containing: {'intent': str, 'entities': dict, 'confidence': float}
        """
        clean_text = text.strip().lower()
        if not clean_text:
            return {"intent": INTENT_UNKNOWN, "entities": {}, "confidence": 0.0}

        # 1. Check for Exact or Prefix match in Custom Commands
        custom_commands = {}
        if self.custom_commands_callback:
            custom_commands = self.custom_commands_callback()

        for trigger, command_data in custom_commands.items():
            trigger_clean = trigger.strip().lower()
            # If the user spoken sentence matches the custom trigger phrase
            if trigger_clean in clean_text:
                return {
                    "intent": INTENT_CUSTOM,
                    "entities": {
                        "trigger": trigger,
                        "command_data": command_data
                    },
                    "confidence": 1.0
                }

        # 2. Vector space intent classification
        best_intent = INTENT_UNKNOWN
        max_similarity = 0.0
        query_vector = text_to_vector(clean_text)

        for intent, patterns in TRAINING_DATA.items():
            for pattern in patterns:
                pattern_vector = text_to_vector(pattern)
                sim = cosine_similarity(query_vector, pattern_vector)
                if sim > max_similarity:
                    max_similarity = sim
                    best_intent = intent

        # Intent heuristic overrides for specific strong keyword indicators
        # (e.g. if query starts with "who is" or "what is" it's general knowledge QA)
        if best_intent in (INTENT_UNKNOWN, INTENT_SEARCH) or max_similarity < 0.2:
            if any(clean_text.startswith(kw) for kw in ["who is", "what is", "tell me about", "who was"]):
                best_intent = INTENT_KNOWLEDGE
                max_similarity = max(max_similarity, 0.4)
            elif any(clean_text.startswith(kw) for kw in ["search for", "google", "search the web for"]):
                best_intent = INTENT_SEARCH
                max_similarity = max(max_similarity, 0.4)

        # Fallback if similarity is extremely low
        if max_similarity < 0.15:
            best_intent = INTENT_UNKNOWN

        # 3. Entity (Slot) Extraction based on determined intent
        entities = {}
        if best_intent == INTENT_SEARCH:
            entities = self._extract_search_entities(clean_text)
        elif best_intent == INTENT_EMAIL:
            entities = self._extract_email_entities(clean_text)
        elif best_intent == INTENT_REMINDER:
            entities = self._extract_reminder_entities(clean_text)
        elif best_intent == INTENT_WEATHER:
            entities = self._extract_weather_entities(clean_text)
        elif best_intent == INTENT_KNOWLEDGE:
            entities = self._extract_knowledge_entities(clean_text)

        return {
            "intent": best_intent,
            "entities": entities,
            "confidence": round(max_similarity, 3)
        }

    def _extract_search_entities(self, text: str) -> dict:
        """Extracts the web search query from the text."""
        # Strips out prefix triggers
        prefixes = [
            r"^search the web for\s+",
            r"^search for\s+",
            r"^google\s+",
            r"^web search\s+",
            r"^look up\s+"
        ]
        query = text
        for prefix in prefixes:
            query = re.sub(prefix, "", query, flags=re.IGNORECASE)
        return {"query": query.strip()}

    def _extract_email_entities(self, text: str) -> dict:
        """Extracts email recipient and body message."""
        entities = {"recipient": "", "body": ""}
        
        # Try to find a literal email address
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if email_match:
            entities["recipient"] = email_match.group(0)
            # Text after the email address is often the body
            parts = text.split(entities["recipient"])
            if len(parts) > 1:
                body_part = parts[1]
                # Clean up transition words like "saying", "that", "message"
                body_part = re.sub(r"^\s*(saying|that|with subject|subject|message)?\s*", "", body_part)
                entities["body"] = body_part.strip()
        else:
            # Pattern: "send email to [name] saying [body]"
            to_match = re.search(r"(?:email|mail|send email to)\s+([\w\s]+?)\s+(?:saying|that|message)\s+(.*)", text)
            if to_match:
                entities["recipient"] = to_match.group(1).strip()
                entities["body"] = to_match.group(2).strip()
            else:
                # Pattern: "send email to [name]"
                to_match_only = re.search(r"(?:email|mail|send email to)\s+([\w\s\.-]+)", text)
                if to_match_only:
                    entities["recipient"] = to_match_only.group(1).strip()
        
        return entities

    def _extract_reminder_entities(self, text: str) -> dict:
        """Extracts duration (in seconds) and reminder topic."""
        entities = {"duration": 0, "message": "Timer alert!"}

        # 1. Parse duration numbers and units
        # e.g., "5 seconds", "ten minutes", "1 hour"
        number_map = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
            "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
            "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
            "fifty": 50, "sixty": 60
        }

        # Patterns matching: "5 seconds", "five minutes", "1 hour"
        time_pattern = r"(\d+|" + "|".join(number_map.keys()) + r")\s+(second|minute|hour|sec|min|hr)s?"
        match = re.search(time_pattern, text)
        
        if match:
            val_str = match.group(1)
            unit = match.group(2)
            
            # Convert value to integer
            if val_str.isdigit():
                val = int(val_str)
            else:
                val = number_map.get(val_str, 0)
                
            # Convert units to seconds
            if "sec" in unit:
                entities["duration"] = val
            elif "min" in unit:
                entities["duration"] = val * 60
            elif "hour" in unit or "hr" in unit:
                entities["duration"] = val * 3600

        # 2. Extract message (what they want to be reminded of)
        # Clean the time pattern from the text (including optional 'in' or 'for' prepositions)
        time_clean_pattern = r"(?:in\s+|for\s+)?(?:(?:\d+|" + "|".join(number_map.keys()) + r")\s+(?:second|minute|hour|sec|min|hr)s?)"
        msg = re.sub(time_clean_pattern, "", text).strip()
        
        # Remove common orchestrator prefix command patterns
        prefixes = [
            r"^set a reminder\s+",
            r"^set reminder\s+",
            r"^remind me\s+",
            r"^set a timer\s+",
            r"^set timer\s+",
            r"^start a timer\s+",
            r"^start timer\s+"
        ]
        for prefix in prefixes:
            msg = re.sub(prefix, "", msg, flags=re.IGNORECASE)
            
        # Strip remaining "to" or "that" at start of the message
        msg = re.sub(r"^(to|that)\s+", "", msg, flags=re.IGNORECASE).strip()
        
        if msg:
            entities["message"] = msg

        return entities

    def _extract_weather_entities(self, text: str) -> dict:
        """Extracts location (city name) from the weather query."""
        # e.g., "weather in New York" -> "New York"
        # e.g., "how is the weather in London today" -> "London"
        match = re.search(r"weather\s+(?:in|at|for)\s+([\w\s]+)", text)
        if match:
            # Strip out relative time references like "today", "tomorrow"
            location = match.group(1).strip()
            location = re.sub(r"\b(today|tomorrow|now)\b", "", location).strip()
            return {"location": location.title()}
        
        # Default to empty if no location is parsed
        return {"location": ""}

    def _extract_knowledge_entities(self, text: str) -> dict:
        """Extracts the search topic from a general knowledge query."""
        prefixes = [
            r"^who is\s+", r"^who was\s+", r"^what is\s+", r"^what was\s+",
            r"^tell me about\s+", r"^search wikipedia for\s+", r"^definition of\s+"
        ]
        query = text
        for prefix in prefixes:
            query = re.sub(prefix, "", query, flags=re.IGNORECASE)
        # Strip trailing punctuation like ?, ., !
        query = re.sub(r"[?!\.]", "", query).strip()
        return {"query": query.title()}
