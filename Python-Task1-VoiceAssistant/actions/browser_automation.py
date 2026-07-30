"""
Browser Automation Action — Playwright-powered web interaction engine.
Enables Nova to control any website: post on Facebook, send WhatsApp messages,
fill forms, click buttons, and perform any web-based task.

Uses Playwright (already installed) in headed mode so the user can see actions live.
"""

import sys
import time
import re
import asyncio
from datetime import datetime
from pathlib import Path
from config.settings import settings

SCREENSHOT_DIR = settings.DATA_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class BrowserAgent:
    """
    Manages a persistent Playwright browser session.
    Allows Nova to navigate, interact, and automate any website.
    """

    def __init__(self):
        self._browser_context = None
        self._page = None
        self._playwright = None

    def _ensure_browser(self):
        """Lazily initialize a persistent browser context (headed = visible to user)."""
        if self._page and not self._page.is_closed():
            return True

        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            
            # Persistent profile directory to retain WhatsApp/Facebook sessions and cookies
            user_data_dir = str(Path(settings.DATA_DIR) / "browser_context")
            
            # Launch persistent browser context (acts as browser + session manager)
            self._browser_context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
            )
            
            # Set default timeout for actions
            self._browser_context.set_default_timeout(15000)
            
            # Get main tab or open a new one
            if self._browser_context.pages:
                self._page = self._browser_context.pages[0]
            else:
                self._page = self._browser_context.new_page()
                
            return True
        except Exception as e:
            print(f"[Browser] Failed to launch persistent browser context: {e}", file=sys.stderr)
            return False

    def execute_task(self, task: str, url: str = None) -> str:
        """
        Execute a browser task described in natural language.
        Routes to specific handlers based on keywords detected in the task.
        """
        print(f"[Browser] Task: {task}")

        if not self._ensure_browser():
            return "Could not launch browser. Please ensure Playwright is installed."

        task_lower = task.lower()

        try:
            # Route to specialized handlers based on task content
            if "whatsapp" in task_lower:
                return self._handle_whatsapp(task)
            elif "facebook" in task_lower:
                return self._handle_facebook(task)
            elif "twitter" in task_lower or "tweet" in task_lower or "x.com" in task_lower:
                return self._handle_twitter(task)
            elif "youtube" in task_lower:
                return self._handle_youtube(task)
            elif "gmail" in task_lower or "google mail" in task_lower:
                return self._handle_gmail(task)
            elif "linkedin" in task_lower:
                return self._handle_linkedin(task)
            elif url:
                return self._navigate_and_act(url, task)
            else:
                return self._generic_browser_task(task)

        except Exception as e:
            print(f"[Browser] Task execution error: {e}", file=sys.stderr)
            return f"Browser task encountered an error: {str(e)}"

    def _navigate(self, url: str, wait_until: str = "domcontentloaded"):
        """Navigate to a URL safely with fast render waiting."""
        try:
            self._page.goto(url, wait_until=wait_until, timeout=20000)
            time.sleep(0.5)
        except Exception as e:
            print(f"[Browser] Navigation error ({url}): {e}", file=sys.stderr)

    def _type_and_submit(self, selector: str, text: str, press_enter: bool = True):
        """Find an element, fill it instantly, and optionally press Enter."""
        try:
            element = self._page.wait_for_selector(selector, timeout=5000)
            element.click()
            time.sleep(0.1)
            element.fill(text)
            time.sleep(0.1)
            if press_enter:
                element.press("Enter")
            return True
        except Exception as e:
            print(f"[Browser] Fill error ({selector}): {e}", file=sys.stderr)
            return False

    def _screenshot(self, label: str = "") -> str:
        """Take a screenshot and return the path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"browser_{label}_{timestamp}.png" if label else f"browser_{timestamp}.png"
        path = SCREENSHOT_DIR / name
        try:
            self._page.screenshot(path=str(path))
            return str(path)
        except Exception:
            return ""

    def _auto_login(self, site_name: str) -> bool:
        """
        Attempts to automatically log in using credentials from the secure local vault
        if a login form is detected on the current page.
        """
        try:
            # Check if there is a password field visible on the screen
            password_field = self._page.locator('input[type="password"]').first
            if not password_field or not password_field.is_visible():
                print(f"[AutoLogin] No login form (password field) detected for {site_name}.")
                return False

            from core import vault
            creds = vault.get_credentials(site_name)
            if not creds:
                print(f"[AutoLogin] No stored credentials found for {site_name} in local vault.")
                return False

            username = creds["username"]
            password = creds["password"]

            print(f"[AutoLogin] Attempting auto-login for {site_name} with user {username}...")

            # Locate username field
            username_field = self._page.locator(
                'input[type="email"], input[type="text"][name*="email" i], input[type="text"][name*="user" i], '
                'input[placeholder*="email" i], input[placeholder*="phone" i], input[placeholder*="username" i]'
            ).first

            if username_field and username_field.is_visible():
                username_field.click()
                username_field.fill(username)
                time.sleep(0.1)

            password_field.click()
            password_field.fill(password)
            time.sleep(0.1)

            # Locate submit/login button
            submit_btn = self._page.locator(
                'button[type="submit"], input[type="submit"], button:has-text("Log In"), '
                'button:has-text("Sign In"), button:has-text("Login"), [role="button"]:has-text("Log In")'
            ).first

            if submit_btn and submit_btn.is_visible():
                submit_btn.click()
                print(f"[AutoLogin] Login form submitted for {site_name}.")
                time.sleep(4)  # Wait for page transitions after login
                return True
            else:
                # Fallback: press Enter on password field
                password_field.press("Enter")
                print(f"[AutoLogin] Login submitted via Enter key.")
                time.sleep(4)
                return True

        except Exception as e:
            print(f"[AutoLogin] Error during auto-login: {e}", file=sys.stderr)
            return False

    # ── Platform-specific handlers ─────────────────────────────────────────

    def _handle_whatsapp(self, task: str) -> str:
        """Handle WhatsApp Web tasks: send messages fastly."""
        # Extract contact name
        contact_match = re.search(
            r"(?:find|contact|message|send to|to)\s+([A-Za-z\s]+?)(?:\s+send|\s+saying|\s+message|\s+with|,|$)",
            task, re.IGNORECASE
        )
        # Extract message content
        msg_match = re.search(
            r"(?:saying|message|send|write)[:\s]+[\"']?(.+?)[\"']?(?:\s+on|\s+via|$)",
            task, re.IGNORECASE
        )

        contact = contact_match.group(1).strip() if contact_match else ""
        message = msg_match.group(1).strip() if msg_match else ""

        # Navigate using domcontentloaded (networkidle is extremely slow for WA Web)
        self._navigate("https://web.whatsapp.com", wait_until="domcontentloaded")

        result_lines = ["Opened WhatsApp Web."]

        try:
            # Smart Wait: wait until either logged-in (search box) or logged-out (QR code) is visible
            print("[Browser] Waiting for WhatsApp interface to load...")
            self._page.wait_for_selector(
                'div[contenteditable="true"][data-tab="3"], canvas, [data-testid="qrcode"]', 
                timeout=25000
            )
        except Exception:
            pass

        # Check if QR code is visible (meaning user needs to log in)
        qr_visible = False
        try:
            qr_visible = self._page.locator('canvas, [data-testid="qrcode"]').first.is_visible()
        except Exception:
            pass

        if qr_visible:
            self._screenshot("whatsapp_login_required")
            return "Please scan the QR code displayed on WhatsApp Web to log in. I've opened the login page for you."

        if contact:
            try:
                # Search for the contact
                search_box = self._page.wait_for_selector(
                    'div[contenteditable="true"][data-tab="3"]', timeout=10000
                )
                search_box.click()
                time.sleep(0.1)
                search_box.fill(contact)
                time.sleep(0.5)

                # Click first result - wait for the chat item row to appear
                # On WA Web, the contact search matches list rows with role="row" or specific title elements
                first_result = self._page.wait_for_selector(
                    f'span[title*="{contact}" i], div[style*="height"] span[title]', 
                    timeout=5000
                )
                first_result.click()
                time.sleep(0.3)

                result_lines.append(f"Opened chat with: {contact}")

                if message:
                    # Find message input (usually contenteditable data-tab="10")
                    msg_box = self._page.wait_for_selector(
                        'div[contenteditable="true"][data-tab="10"]', timeout=5000
                    )
                    msg_box.click()
                    time.sleep(0.1)
                    msg_box.fill(message)
                    time.sleep(0.2)
                    msg_box.press("Enter")
                    time.sleep(0.3)

                    result_lines.append(f"Message sent to {contact}: '{message}'")
                    self._screenshot("whatsapp_sent")
                else:
                    result_lines.append("Chat opened. No message specified to send.")

            except Exception as e:
                result_lines.append(f"Could not locate or message contact '{contact}'. Error details: {e}")
                self._screenshot("whatsapp_error")
        else:
            result_lines.append("WhatsApp Web is open and logged in.")

        return "\n".join(result_lines)


    def _handle_facebook(self, task: str) -> str:
        """Handle Facebook tasks: post status updates."""
        # Extract post content
        post_match = re.search(
            r"(?:post|write|say|status)[:\s]+[\"']?(.+?)[\"']?(?:\s+on facebook|$)",
            task, re.IGNORECASE
        )
        post_content = post_match.group(1).strip() if post_match else ""

        self._navigate("https://www.facebook.com", wait_until="domcontentloaded")
        time.sleep(1)

        # Auto-login if login form is detected
        self._auto_login("facebook")

        result_lines = ["Opened Facebook."]

        if post_content:
            try:
                # Look for the "What's on your mind?" post composer
                composer = self._page.wait_for_selector(
                    'div[data-pagelet="FeedComposer"] [role="button"]',
                    timeout=8000
                )
                composer.click()
                time.sleep(1.5)

                # Type in the post content
                text_area = self._page.wait_for_selector(
                    'div[aria-label*="mind"], div[aria-label*="post"], div[contenteditable="true"]',
                    timeout=5000
                )
                text_area.click()
                time.sleep(0.3)
                text_area.type(post_content, delay=40)
                time.sleep(1)

                result_lines.append(f"Typed post content: '{post_content}'")
                result_lines.append(
                    "Post is ready. Review it in the browser and click 'Post' to publish, "
                    "or tell me 'click post' to do it automatically."
                )
                self._screenshot("facebook_post_ready")

            except Exception as e:
                result_lines.append(
                    f"Could not open post composer: {e}. "
                    "You may need to log into Facebook first in the browser."
                )
        else:
            result_lines.append("Facebook is open. What would you like to post?")

        return "\n".join(result_lines)

    def _handle_twitter(self, task: str) -> str:
        """Handle Twitter/X tasks: compose tweets."""
        tweet_match = re.search(
            r"(?:tweet|post|write|say)[:\s]+[\"']?(.+?)[\"']?(?:\s+on twitter|\s+on x|$)",
            task, re.IGNORECASE
        )
        tweet_content = tweet_match.group(1).strip() if tweet_match else ""

        self._navigate("https://twitter.com/compose/tweet", wait_until="domcontentloaded")
        time.sleep(2)

        # Auto-login if login form is detected
        self._auto_login("twitter")

        result_lines = ["Opened Twitter/X."]

        if tweet_content:
            try:
                tweet_box = self._page.wait_for_selector(
                    'div[data-testid="tweetTextarea_0"]', timeout=8000
                )
                tweet_box.click()
                time.sleep(0.5)
                tweet_box.type(tweet_content, delay=30)
                time.sleep(1)
                result_lines.append(f"Composed tweet: '{tweet_content}'. Review in browser and click Post.")
                self._screenshot("twitter_composed")
            except Exception as e:
                result_lines.append(f"Could not find tweet box: {e}. Please log in to Twitter first.")
        else:
            result_lines.append("Twitter is open. What would you like to tweet?")

        return "\n".join(result_lines)

    def _handle_youtube(self, task: str) -> str:
        """Handle YouTube: open, search videos."""
        search_match = re.search(
            r"(?:search|find|look for|play)[:\s]+[\"']?(.+?)[\"']?(?:\s+on youtube|$)",
            task, re.IGNORECASE
        )
        query = search_match.group(1).strip() if search_match else ""

        self._navigate("https://www.youtube.com")
        time.sleep(2)

        if query:
            try:
                search_box = self._page.wait_for_selector(
                    'input#search', timeout=5000
                )
                search_box.fill(query)
                search_box.press("Enter")
                time.sleep(2)
                return f"Searched YouTube for: '{query}'"
            except Exception as e:
                return f"Opened YouTube but could not search: {e}"
        return "Opened YouTube."

    def _handle_gmail(self, task: str) -> str:
        """Handle Gmail compose flow."""
        self._navigate("https://mail.google.com")
        time.sleep(2)

        try:
            compose_btn = self._page.wait_for_selector(
                'div[gh="cm"]', timeout=5000
            )
            compose_btn.click()
            time.sleep(1)
            return "Opened Gmail and started a new compose window. Gmail is now open in the browser."
        except Exception as e:
            return f"Opened Gmail. Could not auto-click compose: {e}"

    def _handle_linkedin(self, task: str) -> str:
        """Handle LinkedIn: open and navigate."""
        self._navigate("https://www.linkedin.com")
        time.sleep(2)
        return "Opened LinkedIn. What would you like to do?"

    def _navigate_and_act(self, url: str, task: str) -> str:
        """Go to a URL and perform a simple described action."""
        self._navigate(url)
        time.sleep(2)
        self._screenshot("navigation")
        return f"Navigated to {url}. Browser is open and ready for further interaction."

    def _generic_browser_task(self, task: str) -> str:
        """Handle generic browsing requests."""
        # Look for a URL in the task
        url_match = re.search(r"https?://\S+|(?:go to|open|visit|navigate to)\s+([\w\.-]+\.\w+)", task, re.IGNORECASE)
        if url_match:
            url = url_match.group(0) if url_match.group(0).startswith("http") else f"https://{url_match.group(1)}"
            self._navigate(url)
            return f"Navigated to {url}"

        # Look for a Google search intent
        search_match = re.search(r"(?:search|google)\s+(?:for\s+)?(.+)", task, re.IGNORECASE)
        if search_match:
            query = search_match.group(1).strip()
            # Clean up the query to strip any leading redundant words like 'google', 'search', 'for'
            query = re.sub(r'^(?:google|search|for|on)\s+', '', query, flags=re.IGNORECASE)
            import urllib.parse
            search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
            self._navigate(search_url)
            return f"Searched Google for: '{query}'"

        return f"Browser is open. Task attempted: {task}"


    def close(self):
        """Close the browser session."""
        try:
            if self._browser_context:
                self._browser_context.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass



# Singleton browser agent — one persistent instance per server session
_browser_agent = None


def get_browser_agent() -> BrowserAgent:
    """Get or create the shared browser agent instance."""
    global _browser_agent
    if _browser_agent is None:
        _browser_agent = BrowserAgent()
    return _browser_agent


def browser_action(task: str, url: str = None) -> str:
    """Public interface for the browser action tool."""
    agent = get_browser_agent()
    return agent.execute_task(task=task, url=url)
