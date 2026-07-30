"""
Web Search action using the standard Python webbrowser library.
"""

import webbrowser
import urllib.parse
from actions.base import BaseAction
from core.nlu import INTENT_SEARCH

class SearchAction(BaseAction):
    @property
    def name(self) -> str:
        return INTENT_SEARCH

    def execute(self, entities: dict) -> dict:
        query = entities.get("query", "").strip()
        
        if not query:
            return {
                "speech": "What would you like me to search for?",
                "ui_data": {"query": "", "opened_url": ""}
            }

        # Check if the query is a direct URL
        is_url = False
        target_url = query
        
        # Standard indicators for direct web page request
        if query.startswith(("http://", "https://")) or (
            "." in query and " " not in query and len(query.split(".")[-1]) >= 2
        ):
            is_url = True
            if not query.startswith(("http://", "https://")):
                target_url = "https://" + query

        if is_url:
            webbrowser.open(target_url)
            speech_text = f"Opening website: {query}"
            opened_url = target_url
        else:
            # Construct a Google Search URL
            encoded_query = urllib.parse.quote_plus(query)
            target_url = f"https://www.google.com/search?q={encoded_query}"
            webbrowser.open(target_url)
            speech_text = f"Searching the web for {query}"
            opened_url = target_url

        return {
            "speech": speech_text,
            "ui_data": {
                "query": query,
                "opened_url": opened_url,
                "type": "website" if is_url else "search_query"
            }
        }
