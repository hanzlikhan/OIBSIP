"""
General Knowledge Action module.
Queries the Wikipedia API to retrieve concise factual definitions/answers.
"""

import sys
from actions.base import BaseAction
from core.nlu import INTENT_KNOWLEDGE

class KnowledgeAction(BaseAction):
    @property
    def name(self) -> str:
        return INTENT_KNOWLEDGE

    def execute(self, entities: dict) -> dict:
        query = entities.get("query", "").strip()
        
        if not query:
            return {
                "speech": "What topic would you like me to look up?",
                "ui_data": {"query": "", "success": False}
            }

        try:
            import wikipedia
            # Set Wikipedia language to English
            wikipedia.set_lang("en")
            
            # Fetch a short summary (limited to 2 sentences for pleasant vocal reading)
            summary = wikipedia.summary(query, sentences=2)
            
            return {
                "speech": summary,
                "ui_data": {
                    "query": query,
                    "result": summary,
                    "source": "Wikipedia",
                    "success": True
                }
            }
            
        except ImportError:
            return {
                "speech": "Wikipedia library is not loaded. I cannot answer general knowledge questions right now.",
                "ui_data": {"query": query, "success": False, "error": "ImportError"}
            }
        except wikipedia.exceptions.DisambiguationError as e:
            # Handle query ambiguities by selecting the first option or listing a few
            options = e.options[:3]
            options_phrase = ", or ".join(options)
            speech_text = f"'{query}' could refer to a few things: {options_phrase}. Could you be more specific?"
            return {
                "speech": speech_text,
                "ui_data": {
                    "query": query,
                    "options": e.options[:5],
                    "error": "DisambiguationError",
                    "success": False
                }
            }
        except wikipedia.exceptions.PageError:
            # Topic not found on Wikipedia
            speech_text = f"I couldn't find any information on '{query}' on Wikipedia. Would you like me to search the web for it?"
            return {
                "speech": speech_text,
                "ui_data": {
                    "query": query,
                    "error": "PageError",
                    "success": False
                }
            }
        except Exception as e:
            # Dynamic network error or other API issues
            print(f"Wikipedia lookup error: {e}", file=sys.stderr)
            speech_text = f"Sorry, I had trouble connecting to the knowledge base to lookup '{query}'."
            return {
                "speech": speech_text,
                "ui_data": {
                    "query": query,
                    "error": "NetworkError",
                    "success": False
                }
            }
