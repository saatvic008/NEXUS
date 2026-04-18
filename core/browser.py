"""
NEXUS Browser Module — Browser Automation via PyAutoGUI
Full voice-controlled browser: open, navigate, type, click, scroll, go back/forward.
Includes WhatsApp Web messaging support.
"""

import os
import platform
import subprocess
import time
import webbrowser

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


class BrowserController:
    """Voice-controlled browser automation using pyautogui."""

    def __init__(self):
        self.os_type = platform.system().lower()
        self.is_windows = self.os_type == "windows"
        self.is_mac = self.os_type == "darwin"
        self.browser_process = None

        if PYAUTOGUI_AVAILABLE:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.3

    def execute(self, entities):
        """
        Route browser commands based on extracted entities.
        Returns a response string.
        """
        url = entities.get("url", "")
        query = entities.get("query", "")
        text_to_type = entities.get("text_to_type", "")
        action = entities.get("action", "")
        whatsapp_contact = entities.get("whatsapp_contact", "")
        whatsapp_message = entities.get("whatsapp_message", "")

        if whatsapp_contact and whatsapp_message:
            return self.send_whatsapp_message(whatsapp_contact, whatsapp_message)
        elif url:
            return self.navigate_to(url)
        elif query:
            return self.search(query)
        elif text_to_type:
            return self.type_text(text_to_type)
        elif action == "scroll_down":
            return self.scroll("down")
        elif action == "scroll_up":
            return self.scroll("up")
        elif action == "back":
            return self.go_back()
        elif action == "forward":
            return self.go_forward()
        elif action == "refresh":
            return self.refresh()
        elif action == "new_tab":
            return self.new_tab()
        elif action == "close_tab":
            return self.close_tab()
        elif action == "click":
            return self.click()
        else:
            return self.open_browser()

    def open_browser(self, url=None):
        """Open the default web browser, optionally to a URL."""
        try:
            if url:
                webbrowser.open(url)
                return f"Opening browser to {url}."
            else:
                if self.is_windows:
                    subprocess.Popen("start msedge", shell=True)
                elif self.is_mac:
                    subprocess.Popen(["open", "-a", "Safari"])
                else:
                    subprocess.Popen(["xdg-open", "https://www.google.com"])
                return "Browser opened."
        except Exception as e:
            return f"Failed to open browser: {e}"

    def navigate_to(self, url):
        """Navigate to a specific URL."""
        if not url.startswith(("http://", "https://", "www.")):
            if "." in url:
                url = "https://" + url
            else:
                return self.search(url)

        if url.startswith("www."):
            url = "https://" + url

        try:
            webbrowser.open(url)
            time.sleep(1)
            return f"Navigating to {url}."
        except Exception as e:
            return f"Navigation failed: {e}"

    def search(self, query):
        """Search for something on Google."""
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        try:
            webbrowser.open(search_url)
            time.sleep(1)
            return f"Searching Google for '{query}'."
        except Exception as e:
            return f"Search failed: {e}"

    def type_text(self, text):
        """Type text into the currently focused input field."""
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot type — pyautogui not installed."

        try:
            time.sleep(0.5)
            pyautogui.typewrite(text, interval=0.03)
            return f"Typed: '{text}'."
        except Exception as e:
            try:
                import pyperclip
                pyperclip.copy(text)
                if self.is_mac:
                    pyautogui.hotkey("command", "v")
                else:
                    pyautogui.hotkey("ctrl", "v")
                return f"Typed: '{text}'."
            except Exception:
                return f"Typing failed: {e}"

    def send_whatsapp_message(self, contact, message):
        """
        Send a WhatsApp message via WhatsApp Web.
        Uses direct coordinate clicking to avoid browser Ctrl+F conflict.
        Coordinates scale automatically based on screen resolution.
        """
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot send WhatsApp message — pyautogui not installed."

        try:
            # Step 1: Open WhatsApp Web
            print(f"[BROWSER] Opening WhatsApp Web...")
            webbrowser.open("https://web.whatsapp.com")

            # Step 2: Wait for page to load fully
            print(f"[BROWSER] Waiting for WhatsApp Web to load...")
            time.sleep(8)

            # Step 3: Press Escape twice to close any popups
            pyautogui.press("escape")
            time.sleep(0.4)
            pyautogui.press("escape")
            time.sleep(0.4)

            # Step 4: Click the WhatsApp search bar directly
            # Coordinates scale to actual screen resolution
            screen_w, screen_h = pyautogui.size()
            print(f"[BROWSER] Screen resolution: {screen_w}x{screen_h}")

            search_x = int(screen_w * 0.145)   # ~14.5% from left
            search_y = int(screen_h * 0.134)   # ~13.4% from top

            print(f"[BROWSER] Clicking WhatsApp search bar at ({search_x}, {search_y})")
            pyautogui.click(search_x, search_y)
            time.sleep(1)

            # Step 5: Clear and type contact name
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)
            print(f"[BROWSER] Searching for contact: {contact}")
            self._safe_type(contact)
            time.sleep(2)

            # Step 6: Press Enter to open first matching chat
            pyautogui.press("enter")
            time.sleep(1.5)

            # Step 7: Click the message input box at the bottom center
            msg_x = int(screen_w * 0.50)    # center horizontally
            msg_y = int(screen_h * 0.935)   # near bottom

            print(f"[BROWSER] Clicking message input at ({msg_x}, {msg_y})")
            pyautogui.click(msg_x, msg_y)
            time.sleep(0.8)

            # Step 8: Type the message
            print(f"[BROWSER] Typing message: {message}")
            self._safe_type(message)
            time.sleep(0.5)

            # Step 9: Press Enter to send
            pyautogui.press("enter")
            time.sleep(0.5)

            print(f"[BROWSER] WhatsApp message sent to {contact}.")
            return f"WhatsApp message sent to {contact}: '{message}'."

        except Exception as e:
            return f"WhatsApp message failed: {e}"

    def _safe_type(self, text):
        """Type text safely using clipboard paste for full Unicode support."""
        try:
            import pyperclip
            pyperclip.copy(text)
            time.sleep(0.2)
            if self.is_mac:
                pyautogui.hotkey("command", "v")
            else:
                pyautogui.hotkey("ctrl", "v")
        except Exception:
            try:
                pyautogui.typewrite(text, interval=0.05)
            except Exception as e:
                print(f"[BROWSER] Typing failed: {e}")

    def scroll(self, direction="down", amount=5):
        """Scroll the page up or down."""
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot scroll — pyautogui not installed."
        try:
            pyautogui.scroll(-amount if direction == "down" else amount)
            return f"Scrolled {direction}."
        except Exception as e:
            return f"Scroll failed: {e}"

    def click(self, x=None, y=None):
        """Click at the current mouse position or specified coordinates."""
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot click — pyautogui not installed."
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y)
                return f"Clicked at ({x}, {y})."
            else:
                pyautogui.click()
                return "Clicked."
        except Exception as e:
            return f"Click failed: {e}"

    def go_back(self):
        """Navigate the browser back."""
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot go back — pyautogui not installed."
        try:
            pyautogui.hotkey("command" if self.is_mac else "alt", "[" if self.is_mac else "left")
            return "Went back."
        except Exception as e:
            return f"Go back failed: {e}"

    def go_forward(self):
        """Navigate the browser forward."""
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot go forward — pyautogui not installed."
        try:
            pyautogui.hotkey("command" if self.is_mac else "alt", "]" if self.is_mac else "right")
            return "Went forward."
        except Exception as e:
            return f"Go forward failed: {e}"

    def refresh(self):
        """Refresh the current page."""
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot refresh — pyautogui not installed."
        try:
            pyautogui.hotkey("command" if self.is_mac else "ctrl", "r")
            return "Page refreshed."
        except Exception as e:
            return f"Refresh failed: {e}"

    def new_tab(self):
        """Open a new browser tab."""
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot open new tab — pyautogui not installed."
        try:
            pyautogui.hotkey("command" if self.is_mac else "ctrl", "t")
            return "New tab opened."
        except Exception as e:
            return f"New tab failed: {e}"

    def close_tab(self):
        """Close the current browser tab."""
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot close tab — pyautogui not installed."
        try:
            pyautogui.hotkey("command" if self.is_mac else "ctrl", "w")
            return "Tab closed."
        except Exception as e:
            return f"Close tab failed: {e}"

    def focus_address_bar(self):
        """Focus the browser address bar."""
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot focus address bar — pyautogui not installed."
        try:
            pyautogui.hotkey("command" if self.is_mac else "ctrl", "l")
            time.sleep(0.3)
            return "Address bar focused."
        except Exception as e:
            return f"Focus address bar failed: {e}"

    def press_enter(self):
        """Press Enter key."""
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot press Enter — pyautogui not installed."
        try:
            pyautogui.press("enter")
            return "Enter pressed."
        except Exception as e:
            return f"Press Enter failed: {e}"


# Convenience singleton
_instance = None

def get_browser():
    """Get or create a singleton BrowserController instance."""
    global _instance
    if _instance is None:
        _instance = BrowserController()
    return _instance
