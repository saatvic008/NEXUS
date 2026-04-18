"""
NEXUS HUD Module — On-Screen Heads-Up Display
Always-on-top tkinter overlay showing assistant status, commands, and responses.
"""

import threading
import time
import json
import os

try:
    import tkinter as tk
    from tkinter import font as tkfont
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False


class HUD:
    """On-screen heads-up display overlay using tkinter."""

    # Status colors
    STATUS_COLORS = {
        "locked": "#e94560",
        "listening": "#00d2d3",
        "processing": "#feca57",
        "speaking": "#54a0ff",
        "idle": "#576574",
        "error": "#ff6348"
    }

    def __init__(self, config_path="config.json"):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config = self._load_config(config_path)
        hud_config = self.config.get("hud", {})

        self.enabled = hud_config.get("enabled", True)
        self.position = hud_config.get("position", "bottom_right")
        self.opacity = hud_config.get("opacity", 0.85)
        self.width = hud_config.get("width", 400)
        self.height = hud_config.get("height", 200)

        # State
        self.current_status = "locked"
        self.last_command = ""
        self.last_response = ""
        self.session_duration = "00:00:00"
        self.interaction_count = 0

        # Tkinter objects
        self.root = None
        self.thread = None
        self.is_visible = False
        self._running = False

        # Label references
        self._status_label = None
        self._status_dot = None
        self._command_label = None
        self._response_label = None
        self._stats_label = None

    def _load_config(self, config_path):
        """Load config."""
        full_path = os.path.join(self.base_dir, config_path)
        try:
            with open(full_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"hud": {}}

    def start(self):
        """Start the HUD in a separate thread."""
        if not TK_AVAILABLE:
            print("[HUD] tkinter not available. HUD disabled.")
            return

        if not self.enabled:
            print("[HUD] HUD disabled in config.")
            return

        self._running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("[HUD] Started.")

    def _run(self):
        """Run the tkinter main loop in a thread."""
        try:
            self.root = tk.Tk()
            self.root.title("NEXUS")
            self.root.overrideredirect(True)  # No title bar
            self.root.attributes("-topmost", True)  # Always on top
            self.root.attributes("-alpha", self.opacity)

            # Dark theme background
            bg_color = "#1a1a2e"
            self.root.configure(bg=bg_color)

            # Set size and position
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x, y = self._get_position(screen_w, screen_h)
            self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

            # Build UI
            self._build_ui(bg_color)

            self.is_visible = True

            # Start periodic update
            self._schedule_update()

            self.root.mainloop()

        except Exception as e:
            print(f"[HUD] Error: {e}")
            self._running = False

    def _get_position(self, screen_w, screen_h):
        """Calculate window position based on config."""
        margin = 20
        positions = {
            "top_left": (margin, margin),
            "top_right": (screen_w - self.width - margin, margin),
            "bottom_left": (margin, screen_h - self.height - margin - 40),
            "bottom_right": (screen_w - self.width - margin, screen_h - self.height - margin - 40),
            "center": ((screen_w - self.width) // 2, (screen_h - self.height) // 2)
        }
        return positions.get(self.position, positions["bottom_right"])

    def _build_ui(self, bg_color):
        """Build the HUD user interface."""
        accent = "#16213e"
        text_color = "#eaeaea"
        muted_color = "#8d99ae"

        # Main frame with padding
        main_frame = tk.Frame(self.root, bg=bg_color, padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header: NEXUS + Status
        header = tk.Frame(main_frame, bg=bg_color)
        header.pack(fill=tk.X, pady=(0, 5))

        title_label = tk.Label(
            header, text="NEXUS", font=("Consolas", 14, "bold"),
            fg="#e94560", bg=bg_color
        )
        title_label.pack(side=tk.LEFT)

        # Status indicator (colored dot + text)
        status_frame = tk.Frame(header, bg=bg_color)
        status_frame.pack(side=tk.RIGHT)

        self._status_dot = tk.Label(
            status_frame, text="●", font=("Consolas", 12),
            fg=self.STATUS_COLORS.get(self.current_status, "#576574"), bg=bg_color
        )
        self._status_dot.pack(side=tk.LEFT, padx=(0, 5))

        self._status_label = tk.Label(
            status_frame, text=self.current_status.upper(),
            font=("Consolas", 10, "bold"),
            fg=self.STATUS_COLORS.get(self.current_status, "#576574"), bg=bg_color
        )
        self._status_label.pack(side=tk.LEFT)

        # Separator
        sep = tk.Frame(main_frame, height=1, bg=accent)
        sep.pack(fill=tk.X, pady=5)

        # Last Command
        cmd_header = tk.Label(
            main_frame, text="LAST COMMAND:", font=("Consolas", 8),
            fg=muted_color, bg=bg_color, anchor="w"
        )
        cmd_header.pack(fill=tk.X)

        self._command_label = tk.Label(
            main_frame, text="—", font=("Consolas", 10),
            fg=text_color, bg=bg_color, anchor="w", wraplength=self.width - 40
        )
        self._command_label.pack(fill=tk.X, pady=(0, 5))

        # Response
        resp_header = tk.Label(
            main_frame, text="RESPONSE:", font=("Consolas", 8),
            fg=muted_color, bg=bg_color, anchor="w"
        )
        resp_header.pack(fill=tk.X)

        self._response_label = tk.Label(
            main_frame, text="—", font=("Consolas", 9),
            fg="#54a0ff", bg=bg_color, anchor="w", wraplength=self.width - 40
        )
        self._response_label.pack(fill=tk.X, pady=(0, 5))

        # Stats bar
        self._stats_label = tk.Label(
            main_frame, text="Session: 00:00:00 | Commands: 0",
            font=("Consolas", 8), fg=muted_color, bg=bg_color, anchor="w"
        )
        self._stats_label.pack(fill=tk.X, side=tk.BOTTOM)

    def _schedule_update(self):
        """Schedule periodic UI update."""
        if self._running and self.root:
            self._refresh_ui()
            self.root.after(500, self._schedule_update)

    def _refresh_ui(self):
        """Refresh all UI elements with current state."""
        try:
            if self._status_label:
                color = self.STATUS_COLORS.get(self.current_status, "#576574")
                self._status_label.config(text=self.current_status.upper(), fg=color)
                self._status_dot.config(fg=color)

            if self._command_label:
                display_cmd = self.last_command if self.last_command else "—"
                if len(display_cmd) > 60:
                    display_cmd = display_cmd[:57] + "..."
                self._command_label.config(text=display_cmd)

            if self._response_label:
                display_resp = self.last_response if self.last_response else "—"
                if len(display_resp) > 80:
                    display_resp = display_resp[:77] + "..."
                self._response_label.config(text=display_resp)

            if self._stats_label:
                self._stats_label.config(
                    text=f"Session: {self.session_duration} | Commands: {self.interaction_count}"
                )

        except tk.TclError:
            pass  # Widget destroyed

    def update_status(self, status):
        """Update the current status."""
        self.current_status = status

    def update_command(self, command):
        """Update the last command text."""
        self.last_command = command

    def update_response(self, response):
        """Update the last response text."""
        self.last_response = response

    def update_stats(self, session_duration, interaction_count):
        """Update session statistics."""
        self.session_duration = session_duration
        self.interaction_count = interaction_count

    def show(self):
        """Show the HUD window."""
        if self.root:
            try:
                self.root.deiconify()
                self.is_visible = True
            except tk.TclError:
                pass

    def hide(self):
        """Hide the HUD window."""
        if self.root:
            try:
                self.root.withdraw()
                self.is_visible = False
            except tk.TclError:
                pass

    def toggle(self):
        """Toggle HUD visibility."""
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def stop(self):
        """Stop the HUD."""
        self._running = False
        if self.root:
            try:
                self.root.destroy()
            except tk.TclError:
                pass
        print("[HUD] Stopped.")


# Convenience singleton
_instance = None

def get_hud(config_path="config.json"):
    """Get or create a singleton HUD instance."""
    global _instance
    if _instance is None:
        _instance = HUD(config_path)
    return _instance
