# AI Computer Control

An AI agent that watches your computer screen in real time and controls it (mouse + keyboard) — operated from your Android phone over Bluetooth.

## Download the Android App

**[Download AIControl.apk](https://github.com/gge2898/Geremoah/releases/latest/download/AIControl.apk)**

> The APK is built automatically by GitHub Actions on every push. If the link above says "Not Found", wait a few minutes for the first build to complete, then try again.

**Install steps:**
1. Click the link above on your Android phone (or transfer the file to your phone)
2. Open the downloaded `AIControl.apk`
3. Tap **Install** — if prompted, allow "Install from unknown sources" in Settings → Security
4. Open the **AI Control** app

```
ANDROID PHONE                     COMPUTER
┌─────────────────┐               ┌──────────────────────────────┐
│ Type a task     │──Bluetooth────▶│ Bluetooth server              │
│                 │               │  ↓ Gemma 3 (via Ollama)       │
│ Watch the AI    │◀──Bluetooth───│  ↓ Sees screen (live video)   │
│ work live       │  status msgs  │  ↓ Controls mouse + keyboard  │
└─────────────────┘               └──────────────────────────────┘
```

**No cloud. No API keys. Gemma 3 runs 100% locally on your computer.**

---

## How it works

1. The computer agent captures the screen as a live video feed (5 frames/sec).
2. When you send a task from your phone, the agent feeds the latest frame to **Gemma 3** running locally via [Ollama](https://ollama.com).
3. Gemma 3 decides what to do (click, type, press a key, etc.) and sends back a tool call.
4. The agent executes the action using PyAutoGUI, captures a fresh frame, and loops until the task is done.
5. Every step is streamed back to your phone in real time.

---

## Setup

### 1 — Computer: Install Ollama and pull Gemma 3

```bash
# Install Ollama (Linux / macOS)
curl -fsSL https://ollama.com/install.sh | sh

# Pull Gemma 3 — choose based on your RAM:
ollama pull gemma3:4b     # ~3 GB RAM — fast, good for simple tasks
ollama pull gemma3:12b    # ~8 GB RAM — smarter, handles complex tasks

# Start Ollama (runs in background)
ollama serve
```

### 2 — Computer: Install Bluetooth dependencies

**Linux:**
```bash
sudo apt install libbluetooth-dev python3-dev
```

**macOS:** No extra steps needed.

**Windows:** Install [PyBluez2 via wheel](https://github.com/pybluez/pybluez).

### 3 — Computer: Install Python dependencies

```bash
cd computer_agent
pip install -r requirements.txt
```

### 4 — Computer: Make it discoverable and run the agent

```bash
# Linux — make Bluetooth discoverable
bluetoothctl discoverable on

# Run the agent (keep this running)
python main.py
```

You'll see:
```
============================================================
  AI Computer Control Agent
  Model : gemma3:4b
  Safety: Move mouse to top-left corner to abort at any time
============================================================

Ollama is running.
Bluetooth server listening on RFCOMM port 1
Waiting for connection...
```

### 5 — Android: Pair the phone with the computer

Go to **Settings → Bluetooth** on your Android phone and pair with your computer. Do this once.

### 6 — Android: Build and install the app

1. Open the `android/` folder in **Android Studio**.
2. Connect your phone via USB (with USB debugging enabled).
3. Click **Run ▶** — the app installs automatically.

Or build an APK: **Build → Build Bundle(s) / APK(s) → Build APK(s)** and transfer it to your phone.

### 7 — Android: Connect and use

1. Open the **AI Control** app.
2. Tap **Connect to Computer** and select your computer from the list.
3. Type a task and tap **Send**.
4. Watch the AI work on your computer screen while status updates stream to your phone.

---

## Usage examples

| Task | What the AI does |
|---|---|
| `open firefox and go to google.com` | Finds Firefox, clicks it, navigates to Google |
| `open a terminal and run ls` | Opens a terminal emulator, types `ls`, presses Enter |
| `find the clock app and set a 5 minute timer` | Navigates the desktop to find and use the clock |
| `take a screenshot and save it to the desktop` | Uses keyboard shortcut or snipping tool |
| `open settings and turn on dark mode` | Navigates system settings |

---

## Safety

- **Failsafe:** Move the mouse to the **top-left corner** of the screen at any time to immediately abort all AI actions.
- **Iteration limit:** The agent stops automatically after 50 steps to prevent runaway loops.
- **Local only:** Gemma 3 runs on your machine; no data is sent to any cloud service.

---

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `gemma3:4b` | Override the model (e.g. `gemma3:12b`) |

Set it before running:
```bash
OLLAMA_MODEL=gemma3:12b python main.py
```

---

## Project structure

```
├── android/                   Android app (Kotlin)
│   └── app/src/main/
│       ├── java/com/aicontrol/
│       │   ├── MainActivity.kt      UI + Bluetooth glue
│       │   ├── BluetoothClient.kt   RFCOMM connection + I/O
│       │   └── TaskViewModel.kt     State management
│       └── res/layout/
│           └── activity_main.xml    UI layout
│
└── computer_agent/            Python agent (runs on computer)
    ├── main.py                Entry point
    ├── server.py              Bluetooth RFCOMM server
    └── agent/
        ├── agent.py           Gemma 3 agent loop (Ollama)
        ├── screen.py          Live video frame capture
        ├── computer.py        PyAutoGUI mouse/keyboard control
        ├── tools.py           Function definitions for Gemma 3
        └── display.py         Terminal output
```

---

## Troubleshooting

**"Cannot reach Ollama"** — Make sure `ollama serve` is running in a separate terminal.

**"No paired Bluetooth devices"** — Pair your phone with the computer in Android Settings → Bluetooth first.

**"Connection failed"** — Make sure `python main.py` is running on the computer and Bluetooth is on.

**AI clicks wrong places** — Try `gemma3:12b` for better spatial accuracy. The 4B model can sometimes mis-estimate coordinates.

**App crashes on Android 12+** — Make sure you grant both BLUETOOTH_CONNECT and BLUETOOTH_SCAN permissions when prompted.
