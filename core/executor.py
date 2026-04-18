"""
NEXUS Executor Module — OS-Level System Execution
Cross-platform system actions: launch apps, control volume, take screenshots, manage files, run commands.
"""

import os
import platform
import subprocess
import time
import json

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import keyboard as kb
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


class Executor:
    """OS-level action executor with cross-platform support."""

    def __init__(self):
        self.os_type = platform.system().lower()  # 'windows', 'darwin', 'linux'
        self.is_windows = self.os_type == "windows"
        self.is_mac = self.os_type == "darwin"
        self.is_linux = self.os_type == "linux"

        # Common app mappings (name -> command)
        self.app_commands = self._build_app_map()

        if PYAUTOGUI_AVAILABLE:
            pyautogui.FAILSAFE = True  # Move mouse to corner to abort

    def _build_app_map(self):
        """Build application name to launch command mapping."""
        if self.is_windows:
            return {
                "notepad": "notepad.exe",
                "calculator": "calc.exe",
                "file explorer": "explorer.exe",
                "explorer": "explorer.exe",
                "command prompt": "cmd.exe",
                "cmd": "cmd.exe",
                "powershell": "powershell.exe",
                "task manager": "taskmgr.exe",
                "paint": "mspaint.exe",
                "wordpad": "wordpad.exe",
                "snipping tool": "snippingtool.exe",
                "control panel": "control.exe",
                "settings": "ms-settings:",
                # Common third-party apps
                "chrome": "chrome",
                "google chrome": "chrome",
                "firefox": "firefox",
                "edge": "msedge",
                "visual studio code": "code",
                "vscode": "code",
                "vs code": "code",
                "spotify": "spotify",
                "discord": "discord",
                "slack": "slack",
                "vlc": "vlc",
                "steam": "steam",
            }
        elif self.is_mac:
            return {
                "finder": "open -a Finder",
                "terminal": "open -a Terminal",
                "safari": "open -a Safari",
                "chrome": "open -a 'Google Chrome'",
                "firefox": "open -a Firefox",
                "vscode": "open -a 'Visual Studio Code'",
                "vs code": "open -a 'Visual Studio Code'",
                "spotify": "open -a Spotify",
                "calculator": "open -a Calculator",
                "notes": "open -a Notes",
                "system preferences": "open -a 'System Preferences'",
            }
        else:
            return {
                "terminal": "x-terminal-emulator",
                "file manager": "xdg-open .",
                "chrome": "google-chrome",
                "firefox": "firefox",
                "vscode": "code",
                "calculator": "gnome-calculator",
            }

    def execute(self, entities):
        """
        Route execution based on extracted entities.
        Returns a response string describing what was done.
        """
        action = entities.get("action", "").lower()
        application = entities.get("application", "").lower()

        # ── App launch/close ──
        if application and action in ("close", "exit"):
            return self.close_application(application)
        elif application:
            return self.open_application(application)

        # ── File/Folder operations ──
        elif action == "create":
            return self.create_file_or_folder(entities)
        elif action == "delete":
            return self.delete_file_or_folder(entities)
        elif action == "rename":
            return self.rename_file_or_folder(entities)

        # ── Screenshot ──
        elif entities.get("screenshot"):
            return self.take_screenshot()

        # ── Volume ──
        elif entities.get("volume"):
            return self.adjust_volume(entities)

        # ── Lock screen ──
        elif entities.get("lock"):
            return self.lock_screen()

        # ── Shutdown ──
        elif entities.get("shutdown"):
            return self.shutdown()

        # ── Restart ──
        elif entities.get("restart"):
            return self.restart()

        else:
            return "I'm not sure what system action to perform."

    def open_application(self, app_name):
        """Launch an application by name."""
        app_name_lower = app_name.lower().strip()
        command = self.app_commands.get(app_name_lower)

        try:
            if command:
                if self.is_windows:
                    if command.startswith("ms-settings:"):
                        os.startfile(command)
                    else:
                        subprocess.Popen(command, shell=True)
                else:
                    subprocess.Popen(command, shell=True)
                return f"Opening {app_name}."
            else:
                # Try to open directly
                if self.is_windows:
                    try:
                        os.startfile(app_name_lower)
                        return f"Opening {app_name}."
                    except FileNotFoundError:
                        subprocess.Popen(f"start {app_name_lower}", shell=True)
                        return f"Trying to open {app_name}."
                else:
                    subprocess.Popen(["open" if self.is_mac else "xdg-open", app_name_lower])
                    return f"Opening {app_name}."

        except Exception as e:
            return f"Couldn't open {app_name}: {e}"

    def close_application(self, app_name):
        """Close an application by name."""
        try:
            if self.is_windows:
                subprocess.run(f"taskkill /IM {app_name}.exe /F", shell=True, capture_output=True)
            elif self.is_mac:
                subprocess.run(["pkill", "-f", app_name], capture_output=True)
            else:
                subprocess.run(["pkill", "-f", app_name], capture_output=True)
            return f"Closed {app_name}."
        except Exception as e:
            return f"Couldn't close {app_name}: {e}"

    def take_screenshot(self, save_path=None):
        """Take a screenshot and save it."""
        if not PYAUTOGUI_AVAILABLE:
            return "Cannot take screenshot — pyautogui not installed."

        if not save_path:
            screenshots_dir = os.path.join(os.path.expanduser("~"), "Pictures", "NEXUS_Screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")

        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(save_path)
            return f"Screenshot saved to {save_path}."
        except Exception as e:
            return f"Screenshot failed: {e}"

    def adjust_volume(self, entities):
        """Adjust system volume up or down."""
        direction = entities.get("direction", "up")

        try:
            if self.is_windows:
                if PYAUTOGUI_AVAILABLE:
                    if direction == "up":
                        pyautogui.press("volumeup", presses=5)
                        return "Volume increased."
                    elif direction == "down":
                        pyautogui.press("volumedown", presses=5)
                        return "Volume decreased."
                    elif direction == "mute":
                        pyautogui.press("volumemute")
                        return "Volume muted."
            elif self.is_mac:
                if direction == "up":
                    subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) + 10)"])
                elif direction == "down":
                    subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) - 10)"])
                elif direction == "mute":
                    subprocess.run(["osascript", "-e", "set volume output muted true"])
                return f"Volume {direction}."

            return "Volume adjusted."
        except Exception as e:
            return f"Volume control failed: {e}"

    def lock_screen(self):
        """Lock the screen."""
        try:
            if self.is_windows:
                subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            elif self.is_mac:
                subprocess.run(["pmset", "displaysleepnow"])
            else:
                subprocess.run(["xdg-screensaver", "lock"])
            return "Screen locked."
        except Exception as e:
            return f"Lock screen failed: {e}"

    def shutdown(self):
        """Shut down the computer."""
        try:
            if self.is_windows:
                subprocess.run("shutdown /s /t 30", shell=True)
                return "System shutting down in 30 seconds. Say 'cancel shutdown' to abort."
            elif self.is_mac:
                subprocess.run(["sudo", "shutdown", "-h", "+1"])
                return "System shutting down in 1 minute."
            return "Shutdown initiated."
        except Exception as e:
            return f"Shutdown failed: {e}"

    def restart(self):
        """Restart the computer."""
        try:
            if self.is_windows:
                subprocess.run("shutdown /r /t 30", shell=True)
                return "System restarting in 30 seconds."
            elif self.is_mac:
                subprocess.run(["sudo", "shutdown", "-r", "+1"])
                return "System restarting in 1 minute."
            return "Restart initiated."
        except Exception as e:
            return f"Restart failed: {e}"

    def create_file_or_folder(self, entities):
        """Create a file or folder."""
        item_type = entities.get("type", "file")
        name = entities.get("name", f"new_{item_type}")
        base_path = os.path.expanduser("~/Desktop")
        full_path = os.path.join(base_path, name)

        try:
            if item_type in ("folder", "directory"):
                os.makedirs(full_path, exist_ok=True)
                return f"Folder '{name}' created on Desktop."
            else:
                with open(full_path, "w") as f:
                    f.write("")
                return f"File '{name}' created on Desktop."
        except Exception as e:
            return f"Failed to create {item_type}: {e}"

    def delete_file_or_folder(self, entities):
        """Delete a file or folder."""
        name = entities.get("name", "")
        if not name:
            return "Please specify the file or folder name to delete."

        base_path = os.path.expanduser("~/Desktop")
        full_path = os.path.join(base_path, name)

        try:
            if os.path.isdir(full_path):
                import shutil
                shutil.rmtree(full_path)
                return f"Folder '{name}' deleted."
            elif os.path.isfile(full_path):
                os.remove(full_path)
                return f"File '{name}' deleted."
            else:
                return f"'{name}' not found on Desktop."
        except Exception as e:
            return f"Failed to delete: {e}"

    def rename_file_or_folder(self, entities):
        """Rename a file or folder."""
        old_name = entities.get("name", "")
        new_name = entities.get("new_name", "")
        if not old_name or not new_name:
            return "Please specify both old and new names."

        base_path = os.path.expanduser("~/Desktop")
        old_path = os.path.join(base_path, old_name)
        new_path = os.path.join(base_path, new_name)

        try:
            os.rename(old_path, new_path)
            return f"Renamed '{old_name}' to '{new_name}'."
        except Exception as e:
            return f"Rename failed: {e}"

    def run_command(self, command_text):
        """Run an arbitrary system command and return output."""
        try:
            result = subprocess.run(
                command_text, shell=True,
                capture_output=True, text=True, timeout=30
            )
            output = result.stdout.strip() or result.stderr.strip()
            return output if output else "Command executed successfully."
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds."
        except Exception as e:
            return f"Command execution failed: {e}"


# Convenience singleton
_instance = None

def get_executor():
    """Get or create a singleton Executor instance."""
    global _instance
    if _instance is None:
        _instance = Executor()
    return _instance
