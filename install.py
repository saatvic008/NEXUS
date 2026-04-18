"""
NEXUS Installer — Cross-Platform Setup and Service Registration
Detects OS, installs dependencies, configures passkey, registers startup service.
"""

import os
import sys
import subprocess
import platform
import json
import hashlib


def print_banner():
    """Print the NEXUS installer banner."""
    print(r"""
    ╔══════════════════════════════════════════════╗
    ║        NEXUS — Installation Wizard           ║
    ║     Intelligent Voice-Activated Assistant     ║
    ╚══════════════════════════════════════════════╝
    """)


def detect_os():
    """Detect the host operating system."""
    os_name = platform.system().lower()
    print(f"[INSTALL] Detected OS: {platform.system()} {platform.release()}")
    print(f"[INSTALL] Python version: {sys.version}")
    return os_name


def install_dependencies():
    """Install all required Python packages from requirements.txt."""
    print("\n[INSTALL] Installing dependencies...")
    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")

    if not os.path.exists(req_file):
        print("[INSTALL] ERROR: requirements.txt not found!")
        return False

    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", req_file, "--quiet"
        ])
        print("[INSTALL] ✓ All dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[INSTALL] ✗ Dependency installation failed: {e}")
        print("[INSTALL] Try running: pip install -r requirements.txt manually")
        return False


def setup_passkey():
    """Guide the user through passkey configuration."""
    print("\n" + "=" * 50)
    print("  PASSKEY SETUP")
    print("=" * 50)
    print("\nYour passkey is a secret phrase that unlocks NEXUS.")
    print("Choose a phrase of at least 3 words that you'll remember.")
    print("Example: 'nexus override alpha'\n")

    passkey = input("Enter your passkey phrase: ").strip()
    if len(passkey) < 3:
        print("[INSTALL] Passkey too short. Using default: 'nexus activate'")
        passkey = "nexus activate"

    # Confirm
    confirm = input("Confirm your passkey: ").strip()
    if confirm != passkey:
        print("[INSTALL] Phrases don't match. Using first entry.")

    # Hash and store
    normalized = " ".join(passkey.lower().strip().split())
    hashed = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    return hashed


def setup_wake_word():
    """Configure the wake word."""
    print("\n" + "=" * 50)
    print("  WAKE WORD SETUP")
    print("=" * 50)
    print("\nThe wake word activates NEXUS from standby mode.")
    print("Default: 'hey nexus'\n")

    wake_word = input("Enter wake word (press Enter for default): ").strip().lower()
    if not wake_word:
        wake_word = "hey nexus"

    print(f"[INSTALL] Wake word set to: '{wake_word}'")
    return wake_word


def update_config(passkey_hash, wake_word):
    """Update config.json with setup values."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        config["passkey_hash"] = passkey_hash
        config["passkey_set"] = True
        config["wake_word"] = wake_word

        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)

        print("[INSTALL] ✓ Configuration saved.")
        return True

    except Exception as e:
        print(f"[INSTALL] ✗ Config update failed: {e}")
        return False


def create_directories():
    """Create required data directories."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dirs = [
        os.path.join(base_dir, "data"),
        os.path.join(base_dir, "data", "charts"),
        os.path.join(base_dir, "data", "exports"),
        os.path.join(base_dir, "models"),
    ]

    for d in dirs:
        os.makedirs(d, exist_ok=True)

    print("[INSTALL] ✓ Data directories created.")


def register_startup_service(os_name):
    """Register NEXUS as a startup service."""
    print("\n" + "=" * 50)
    print("  STARTUP SERVICE REGISTRATION")
    print("=" * 50)

    auto_start = input("\nStart NEXUS automatically at login? (y/n): ").strip().lower()
    if auto_start != "y":
        print("[INSTALL] Skipping startup registration.")
        return

    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    python_path = sys.executable

    if os_name == "windows":
        _register_windows_startup(python_path, script_path)
    elif os_name == "darwin":
        _register_macos_startup(python_path, script_path)
    else:
        _register_linux_startup(python_path, script_path)


def _register_windows_startup(python_path, script_path):
    """Register as a Windows startup task using Task Scheduler."""
    try:
        task_name = "NEXUS_Assistant"
        cmd = (
            f'schtasks /create /tn "{task_name}" '
            f'/tr "\\\"{python_path}\\\" \\\"{script_path}\\\"" '
            f'/sc onlogon /rl highest /f'
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"[INSTALL] ✓ Registered as Windows startup task: {task_name}")
        else:
            print(f"[INSTALL] ✗ Task Scheduler registration failed: {result.stderr}")
            print("[INSTALL] Try running the installer as Administrator.")

            # Fallback: startup folder shortcut
            _create_startup_shortcut(python_path, script_path)

    except Exception as e:
        print(f"[INSTALL] ✗ Startup registration error: {e}")


def _create_startup_shortcut(python_path, script_path):
    """Create a batch file in the Windows Startup folder as fallback."""
    try:
        startup_dir = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
        )
        bat_path = os.path.join(startup_dir, "NEXUS.bat")
        with open(bat_path, "w") as f:
            f.write(f'@echo off\nstart "" "{python_path}" "{script_path}"\n')
        print(f"[INSTALL] ✓ Created startup batch file: {bat_path}")
    except Exception as e:
        print(f"[INSTALL] ✗ Startup shortcut failed: {e}")


def _register_macos_startup(python_path, script_path):
    """Register as a macOS launchd service via plist."""
    try:
        plist_dir = os.path.expanduser("~/Library/LaunchAgents")
        os.makedirs(plist_dir, exist_ok=True)
        plist_path = os.path.join(plist_dir, "com.nexus.assistant.plist")

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.nexus.assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/nexus.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/nexus.error.log</string>
</dict>
</plist>"""

        with open(plist_path, "w") as f:
            f.write(plist_content)

        subprocess.run(["launchctl", "load", plist_path], capture_output=True)
        print(f"[INSTALL] ✓ Registered as macOS launchd service: {plist_path}")

    except Exception as e:
        print(f"[INSTALL] ✗ macOS service registration failed: {e}")


def _register_linux_startup(python_path, script_path):
    """Register as a Linux autostart entry."""
    try:
        autostart_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(autostart_dir, exist_ok=True)
        desktop_path = os.path.join(autostart_dir, "nexus.desktop")

        desktop_content = f"""[Desktop Entry]
Type=Application
Name=NEXUS Assistant
Exec={python_path} {script_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
        with open(desktop_path, "w") as f:
            f.write(desktop_content)

        print(f"[INSTALL] ✓ Registered as Linux autostart: {desktop_path}")

    except Exception as e:
        print(f"[INSTALL] ✗ Linux autostart registration failed: {e}")


def run_post_install_check():
    """Run a quick check to verify critical imports."""
    print("\n[INSTALL] Running post-install checks...")
    checks = {
        "SpeechRecognition": "speech_recognition",
        "pyttsx3": "pyttsx3",
        "pyautogui": "pyautogui",
        "numpy": "numpy",
        "sympy": "sympy",
    }

    all_ok = True
    for name, module in checks.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} — not installed")
            all_ok = False

    # Optional checks
    optional = {
        "vosk": "vosk",
        "matplotlib": "matplotlib",
        "wikipedia-api": "wikipediaapi",
        "keyboard": "keyboard",
    }

    for name, module in optional.items():
        try:
            __import__(module)
            print(f"  ✓ {name} (optional)")
        except ImportError:
            print(f"  ⚠ {name} (optional — not installed)")

    return all_ok


def main():
    """Run the NEXUS installation wizard."""
    print_banner()

    # Step 1: Detect OS
    os_name = detect_os()

    # Step 2: Create directories
    create_directories()

    # Step 3: Install dependencies
    success = install_dependencies()
    if not success:
        print("\n[INSTALL] ⚠ Some dependencies failed to install.")
        proceed = input("Continue anyway? (y/n): ").strip().lower()
        if proceed != "y":
            print("[INSTALL] Installation cancelled.")
            return

    # Step 4: Post-install check
    run_post_install_check()

    # Step 5: Set up passkey
    passkey_hash = setup_passkey()

    # Step 6: Set up wake word
    wake_word = setup_wake_word()

    # Step 7: Update config
    update_config(passkey_hash, wake_word)

    # Step 8: Register startup service
    register_startup_service(os_name)

    # Done
    print("\n" + "=" * 50)
    print("  INSTALLATION COMPLETE ✓")
    print("=" * 50)
    print(f"\n  Wake word: '{wake_word}'")
    print(f"  Passkey: [hashed and stored securely]")
    print(f"\n  To start NEXUS, run:")
    print(f"    python main.py")
    print(f"\n  To run tests:")
    print(f"    python -m pytest tests/ -v")
    print()


if __name__ == "__main__":
    main()
