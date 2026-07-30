"""
Real-Time Web Search Action
Uses DuckDuckGo (no API key required) to search the live internet.
For deep answers, fetches and reads actual web page content.
"""

import sys
import httpx
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

try:
    from readability import Document
    HAS_READABILITY = True
except ImportError:
    HAS_READABILITY = False


def web_search(query: str, fetch_page: bool = False, max_results: int = 5) -> str:
    """
    Search DuckDuckGo and return formatted results.
    If fetch_page=True, reads the top result's full content for a deeper answer.

    Returns a formatted string the LLM can read and summarize.
    """
    print(f"[WebSearch] Searching: '{query}' | fetch_page={fetch_page}")

    results_text = f"Search results for: '{query}'\n\n"
    top_url = None

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No results found for '{query}'. Try rephrasing."

        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            body = r.get("body", "")
            href = r.get("href", "")
            results_text += f"{i}. **{title}**\n   {body}\n   Source: {href}\n\n"

            if i == 1:
                top_url = href

    except Exception as e:
        print(f"[WebSearch] DuckDuckGo error: {e}", file=sys.stderr)
        return f"Web search failed: {str(e)}. Please check your internet connection."

    # Deep read the top URL if requested
    if fetch_page and top_url:
        page_content = _fetch_page_content(top_url)
        if page_content:
            # Truncate to avoid overwhelming the LLM context
            results_text += f"\n--- Full content from top result ({top_url}) ---\n"
            results_text += page_content[:3000]
            results_text += "\n--- End of page content ---\n"

    return results_text


def search_news(query: str, max_results: int = 5) -> str:
    """Search for recent news articles on a topic."""
    print(f"[WebSearch] News search: '{query}'")
    results_text = f"Latest news for: '{query}'\n\n"

    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))

        if not results:
            return f"No news found for '{query}'."

        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            body = r.get("body", "")
            source = r.get("source", "")
            date = r.get("date", "")
            url = r.get("url", "")
            results_text += f"{i}. **{title}** [{source}] {date}\n   {body}\n   URL: {url}\n\n"

    except Exception as e:
        print(f"[WebSearch] News error: {e}", file=sys.stderr)
        return f"News search failed: {str(e)}"

    return results_text


def _fetch_page_content(url: str) -> str:
    """Fetch and extract clean readable text from a web page."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            response = client.get(url, headers=headers)

        if response.status_code != 200:
            return ""

        html = response.text

        if HAS_READABILITY:
            doc = Document(html)
            # Get article text, strip HTML tags manually
            import re
            text = re.sub(r"<[^>]+>", " ", doc.summary())
            text = re.sub(r"\s+", " ", text).strip()
            return text[:3000]
        else:
            # Basic fallback: strip all HTML tags
            import re
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:2000]

    except Exception as e:
        print(f"[WebSearch] Page fetch error ({url}): {e}", file=sys.stderr)
        return ""
