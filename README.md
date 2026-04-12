# AI Computer Control

An AI agent that watches your computer screen in real time and controls it (mouse + keyboard) — operated from your Android phone over Bluetooth. **Nothing needs to be manually installed on the computer.**

```
ANDROID PHONE                     COMPUTER
┌─────────────────┐               ┌──────────────────────────────┐
│ Type a task     │──Bluetooth────▶│ Single executable             │
│                 │               │  ↓ Auto-installs Ollama       │
│ Watch the AI    │◀──Bluetooth───│  ↓ Gemma 3 AI (local)        │
│ work live       │  status msgs  │  ↓ Sees screen (video feed)  │
│                 │               │  ↓ Controls mouse + keyboard  │
└─────────────────┘               └──────────────────────────────┘
```

No cloud. No API keys. Gemma 3 runs 100% locally on your computer.

---

## Downloads

### Android App

**[Download AIControl.apk](https://github.com/gge2898/Geremoah/releases/latest/download/AIControl.apk)**

Install: open the APK on your phone → tap Install → allow "Install from unknown sources" if prompted.

---

### Computer Agent (pick your OS)

| OS | Download | Run |
|---|---|---|
| Linux | [AIControlAgent-linux](https://github.com/gge2898/Geremoah/releases/latest/download/AIControlAgent-linux) | `chmod +x AIControlAgent-linux && ./AIControlAgent-linux` |
| Windows | [AIControlAgent-windows.exe](https://github.com/gge2898/Geremoah/releases/latest/download/AIControlAgent-windows.exe) | Double-click |
| macOS | [AIControlAgent-macos](https://github.com/gge2898/Geremoah/releases/latest/download/AIControlAgent-macos) | `chmod +x AIControlAgent-macos && ./AIControlAgent-macos` |

**First launch:** The agent automatically downloads and installs Ollama + Gemma 3 (~3 GB, one-time). After that it starts instantly on every subsequent launch.

---

## How to use

1. **Run the computer agent** (download above, double-click or run from terminal).
   - First launch takes a few minutes to set up automatically.
   - You'll see: `Waiting for Android app to connect...`

2. **Pair your phone** with the computer via Bluetooth:
   - Android Settings → Bluetooth → pair with your computer (one-time).

3. **Open the AI Control app** on your phone:
   - Tap **Connect to Computer** → select your computer.
   - Type a task → tap **Send**.
   - Watch the AI work while status updates stream to your phone.

---

## Example tasks

| What you type | What the AI does |
|---|---|
| `open firefox and go to google.com` | Finds and opens Firefox, navigates to Google |
| `open a terminal and run ls -la` | Opens a terminal, types the command, presses Enter |
| `set the volume to 50%` | Uses keyboard shortcuts or system settings |
| `take a screenshot and save it to the desktop` | Uses screenshot shortcut, saves file |
| `open settings and enable dark mode` | Navigates system settings |

---

## Safety

- **Failsafe:** Move the mouse to the **top-left corner** of the screen to immediately stop all AI actions.
- **Iteration limit:** Agent stops automatically after 50 steps.
- **Local only:** Gemma 3 runs on your machine — no data ever leaves your computer.

---

## Configuration (optional)

To use the smarter 12B model instead of the default 4B, set an environment variable before running:

**Linux / macOS:**
```bash
OLLAMA_MODEL=gemma3:12b ./AIControlAgent-linux
```

**Windows (Command Prompt):**
```
set OLLAMA_MODEL=gemma3:12b
AIControlAgent-windows.exe
```

---

## Project structure

```
├── android/                   Android app (Kotlin)
│   └── app/src/main/java/com/aicontrol/
│       ├── MainActivity.kt        UI + Bluetooth glue
│       ├── BluetoothClient.kt     RFCOMM connection + I/O
│       └── TaskViewModel.kt       State management
│
└── computer_agent/            Python agent (compiled to single binary by CI)
    ├── main.py                Entry point + first-run banner
    ├── setup_manager.py       Auto-installs Ollama + pulls Gemma 3
    ├── server.py              Bluetooth RFCOMM server
    └── agent/
        ├── agent.py           Gemma 3 loop (Ollama)
        ├── screen.py          Live video frame capture (5 FPS)
        ├── computer.py        PyAutoGUI mouse/keyboard control
        ├── tools.py           Function definitions for Gemma 3
        └── display.py         Terminal output
```

---

## Troubleshooting

**"Waiting for Android app to connect" but app can't find the computer**
→ Make sure you've paired the phone and computer via Bluetooth Settings first (one-time step).

**First launch stuck at "Downloading Ollama..."**
→ Check your internet connection. The agent downloads ~3 GB on first run.

**AI clicks wrong locations**
→ Try `OLLAMA_MODEL=gemma3:12b` for better accuracy. The 4B model can sometimes misjudge coordinates.

**macOS: "Cannot be opened because the developer cannot be verified"**
→ Right-click the file → Open → Open (bypasses Gatekeeper for unsigned apps).

**Windows: antivirus flags the .exe**
→ PyInstaller bundles trigger some AV false positives. Add an exclusion or build from source.
