# NEXUS
Simulation-based intelligent assistant using adaptive learning, probabilistic decision-making, and real-time system automation.
# NEXUS — Intelligent Voice-Activated System Control Assistant

**An AI-powered, voice-unlocked, voice-operated computer control system with simulation-based decision intelligence.**

---

## Overview

NEXUS is a locally deployable, cross-platform intelligent assistant built entirely in Python, designed to give users complete **hands-free control over their computer through voice commands**. Inspired by J.A.R.V.I.S., NEXUS transforms any Windows or macOS machine into a voice-responsive system — capable of launching applications, controlling the browser, typing and navigating on behalf of the user, answering questions, making simulation-based decisions, and enforcing user identity through a **custom voice passkey security system**.

---

## Key Features

### 🔐 Voice Passkey Security System
- SHA-256 hashed spoken passphrases
- 3-attempt lockout with configurable cooldown
- Idle auto-lock timer
- Failed attempt logging with timestamps

### 🎤 Two-Phase Listening Architecture
- **Passive:** Low-power wake word detection
- **Active:** Full command capture after activation
- Supports Google Speech-to-Text (online) and Vosk (offline)

### 🧠 Natural Language Understanding (NLU)
5 intent categories with keyword scoring + regex:
- System Execution
- Browser Control
- Question Answering
- Simulation Decision
- System Configuration

### 💻 System-Level Execution
- Launch/close apps by name
- Take screenshots
- Adjust volume/brightness
- File operations (create, rename, move, delete)
- Lock/shutdown/restart

### 🌐 Browser Automation
- Open browser, navigate to URLs
- Type in search bars and input fields via pyautogui
- Click, scroll, go back/forward
- Full hands-free web browsing

### 📚 Question Answering
- Instructor Q&A knowledge base (JSON)
- Math calculations via sympy
- Wikipedia lookups
- Time, date, and weather queries

### 📊 Simulation-Based Decision Engine
- Monte Carlo sampling (N=1000 scenarios)
- Weighted multi-criteria utility functions
- RL-inspired memory boost from past decisions
- Matplotlib visualization
- 3 built-in domains: Traffic, Resource, General

### 🧪 Persistent Memory & Adaptive Learning
- JSON interaction log
- Priority cache for frequent commands
- Correction tracking for self-improvement
- Exportable/clearable via voice

### 🖥️ On-Screen HUD
- Always-on-top tkinter overlay
- Shows status: Locked / Listening / Processing / Speaking
- Last command and response display
- Session statistics

---

## Architecture

```
NEXUS/
├── main.py                    # Main orchestrator
├── install.py                 # Cross-platform installer
├── config.json                # System configuration
├── requirements.txt           # Dependencies
├── README.md
├── core/
│   ├── __init__.py
│   ├── tts.py                 # Text-to-Speech (pyttsx3)
│   ├── listener.py            # Wake word + command listener
│   ├── auth.py                # Voice passkey security
│   ├── nlu.py                 # Intent classification
│   ├── executor.py            # OS-level execution
│   ├── browser.py             # Browser automation
│   ├── qa.py                  # Question answering
│   ├── decision_engine.py     # Simulation engine
│   ├── memory.py              # Persistent memory
│   └── hud.py                 # On-screen HUD
├── modules/
│   ├── __init__.py
│   ├── traffic_sim.py         # Traffic route optimization
│   ├── resource_sim.py        # Resource allocation
│   └── general_sim.py         # General decision analysis
├── data/
│   ├── qa_knowledge.json      # Instructor Q&A knowledge base
│   ├── memory_log.json        # Interaction history
│   └── decision_history.json  # Decision records
└── tests/
    ├── __init__.py
    ├── test_auth.py
    ├── test_nlu.py
    ├── test_qa.py
    ├── test_decision_engine.py
    └── test_memory.py
```

---

## Installation

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/NEXUS.git
cd NEXUS

# 2. Run the installer
python install.py

# 3. Start NEXUS
python main.py
```

### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Start the assistant
python main.py
```

---

## Usage

### Voice Commands

| Command | Intent | Action |
|---------|--------|--------|
| "Open Notepad" | System | Launches Notepad |
| "Take a screenshot" | System | Saves screenshot |
| "Open Chrome and go to YouTube" | Browser | Opens browser, navigates |
| "Type in the search bar: Python tutorials" | Browser | Types text into active field |
| "What is machine learning?" | Q&A | Searches KB + Wikipedia |
| "Calculate 25 times 47" | Q&A | Returns 1175 |
| "Help me decide between route A and route B" | Simulation | Runs Monte Carlo analysis |
| "Change my passkey" | Config | Guides through passkey change |
| "Clear memory" | Config | Clears interaction history |

### Configuration

Edit `config.json` to customize:
- Wake word
- Idle timeout duration
- TTS voice and speed
- HUD position and opacity
- Speech recognition engine (Google/Vosk)

---

## Libraries Used

| Library | Purpose |
|---------|---------|
| `SpeechRecognition` | Voice input capture |
| `Vosk` | Offline speech-to-text |
| `pyttsx3` | Text-to-speech output |
| `pyautogui` | System + browser automation |
| `keyboard` | Global hotkeys |
| `numpy` | Monte Carlo simulation |
| `matplotlib` | Decision visualization |
| `sympy` | Math calculations |
| `wikipedia-api` | Factual Q&A |
| `requests` | Weather API |
| `tkinter` | On-screen HUD |
| `hashlib` | Passkey security |
| `pytest` | Unit testing |

---

## Testing

```bash
python -m pytest tests/ -v
```

Tests cover:
- ✅ Passkey hashing, verification, and lockout logic
- ✅ Intent classification across all 5 categories
- ✅ Knowledge base search and math evaluation
- ✅ Simulation engine scoring and domain loading
- ✅ Memory logging, priority cache, and export

---

## License

This project is developed as part of an academic submission for ISSD (Intelligent Systems Simulation and Design).

---

**NEXUS** — *Your voice is the command. The machine is the extension.*

## 👨‍💻 Contributors

- [Chetan Saatvic Reddy](https://github.com/saatvic008)
- [Srichaithra](https://github.com/vyshnavii-007)
